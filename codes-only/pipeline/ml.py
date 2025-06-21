import os
import sys
import pickle
from datetime import datetime

from pyspark.sql import SparkSession, functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator

from signals import (
    ML_SIG_DONE,
    print_signal_mapping
)

# === CONFIGURATION ===
HIVE_DB          = "fraud_detection"
HIVE_TABLE       = "preprocessed_full"
LOCAL_MODEL_PATH = "fraud_logreg.pkl"


def init_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("ml_pipeline.py")
        .config("spark.driver.memory", "10g")
        .config("spark.executor.memory", "10g")
        .config("spark.hadoop.fs.s3a.impl",        "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.access.key",  os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
        .config("spark.hadoop.fs.s3a.secret.key",  os.getenv("MINIO_SECRET_KEY", "minioadmin"))
        .config("spark.hadoop.fs.s3a.endpoint",    os.getenv("MINIO_ENDPOINT", "http://localhost:9000"))
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .enableHiveSupport()
        .getOrCreate()
    )


def main():
    watcher_pid = int(sys.argv[1]) if len(sys.argv) > 1 else None

    # Only emit final "Done" signal
    print_signal_mapping(
        file_signals={},
        extra_signals={"All ML steps done": ML_SIG_DONE},
        title="ML Pipeline Signal Mapping"
    )

    # load data from Hive
    spark = init_spark()
    df = spark.table(f"{HIVE_DB}.{HIVE_TABLE}")

    # feature engineering
    cat_cols = ["card_brand", "card_type", "merchant_state"]
    indexers = [
        StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="keep")
        for c in cat_cols
    ]
    encoders = [
        OneHotEncoder(inputCol=f"{c}_idx", outputCol=f"{c}_ohe")
        for c in cat_cols
    ]
    df = df.withColumn(
        "use_chip_bool",
        F.when(F.lower(F.col("use_chip")).contains("chip"), 1).otherwise(0)
    )

    num_cols = [
        "amount", "use_chip_bool",
        "credit_limit", "per_capita_income", "yearly_income", "total_debt",
        "credit_score", "num_credit_cards"
    ]
    assembler = VectorAssembler(
        inputCols=[f"{c}_ohe" for c in cat_cols] + num_cols,
        outputCol="features",
        handleInvalid="keep"
    )

    # build pipeline
    lr = LogisticRegression(
        labelCol="label",
        featuresCol="features",
        maxIter=20,
        regParam=0.1
    )
    pipeline = Pipeline(stages=indexers + encoders + [assembler, lr])

    # train/test split
    train, test = df.randomSplit([0.8, 0.2], seed=42)
    model = pipeline.fit(train)

    # evaluation
    preds = model.transform(test)
    evaluator = BinaryClassificationEvaluator(
        labelCol="label",
        rawPredictionCol="rawPrediction",
        metricName="areaUnderROC"
    )
    auc = evaluator.evaluate(preds)
    print(f"→ Test AUC = {auc:.4f}")

    # export just the LogisticRegressionModel parameters
    lrModel     = model.stages[-1]
    coeffs      = lrModel.coefficients.toArray()
    intercept   = float(lrModel.intercept)
    feature_cols= assembler.getInputCols()

    with open(LOCAL_MODEL_PATH, "wb") as f:
        pickle.dump({
            "coefficients": coeffs,
            "intercept":    intercept,
            "feature_cols": feature_cols
        }, f)
    print(f"→ Model saved to {LOCAL_MODEL_PATH}")

    # final signal & cleanup
 # On envoie uniquement le signal de fin à l'orchestrateur
    if watcher_pid:
        os.kill(watcher_pid, ML_SIG_DONE)
   # Puis on quitte proprement avec code 0
    sys.exit(0)

    spark.stop()


if __name__ == "__main__":
    main()
