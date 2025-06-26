#!/usr/bin/env python3
import os
import sys
import mlflow_minio_artifact_repo
from mlflow.tracking import MlflowClient
from pyspark.ml import PipelineModel
import cloudpickle
from pathlib import Path
from mlflow import artifacts
import mlflow.spark
import mlflow
import matplotlib.pyplot as plt
from pyspark.sql import SparkSession, functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier, GBTClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator, MulticlassClassificationEvaluator

# --- CONFIGURATION ---
HIVE_DB       = "fraud_detection"
HIVE_TABLE    = "preprocessed_full"
MLFLOW_URI    = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT    = os.getenv("MLFLOW_EXPERIMENT", "fraud_detection_exp")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

# Paramètres de ressources
DRIVER_MEMORY   = os.getenv("SPARK_DRIVER_MEMORY", "8g")
EXECUTOR_MEMORY = os.getenv("SPARK_EXECUTOR_MEMORY", "8g")
EXECUTOR_CORES  = os.getenv("SPARK_EXECUTOR_CORES", "1")
NUM_EXECUTORS   = os.getenv("SPARK_EXECUTOR_INSTANCES", "1")

# Initialisation MLflow
mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment(EXPERIMENT)

# Set environment variables for MLflow S3 compatibility
os.environ["AWS_ACCESS_KEY_ID"] = MINIO_ACCESS_KEY
os.environ["AWS_SECRET_ACCESS_KEY"] = MINIO_SECRET_KEY
os.environ["MLFLOW_S3_ENDPOINT_URL"] = f"http://{MINIO_ENDPOINT}"

# --- INITIALISATION SPARK ---
def init_spark():
    builder = SparkSession.builder.appName("ml_pipeline_compare") \
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT) \
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.local.LocalFileSystem") \
        .config("spark.hadoop.fs.AbstractFileSystem.file.impl", "org.apache.hadoop.fs.local.LocalFs") \
        .enableHiveSupport()

    if DRIVER_MEMORY:
        builder = builder.config("spark.driver.memory", DRIVER_MEMORY)
        builder = builder.config("spark.executor.memory", EXECUTOR_MEMORY)
    builder = builder.config("spark.executor.cores", EXECUTOR_CORES)
    builder = builder.config("spark.executor.instances", NUM_EXECUTORS)

    return builder.getOrCreate()

# --- PRÉ-TRAITEMENT PIPELINE ---
def prep_pipeline(cat_cols, num_cols, assembler_out="features"):
    indexers = [StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="keep") for c in cat_cols]
    encoders = [OneHotEncoder(inputCol=f"{c}_idx", outputCol=f"{c}_ohe") for c in cat_cols]
    assembler = VectorAssembler(
        inputCols=[f"{c}_ohe" for c in cat_cols] + num_cols,
        outputCol=assembler_out,
        handleInvalid="keep"
    )
    return indexers + encoders + [assembler]

# --- PROGRAMME PRINCIPAL ---
def main():
    watcher_pid = int(sys.argv[1]) if len(sys.argv) > 1 else None

    spark = init_spark()
    sc = spark.sparkContext

    print(f"YARN application id: {sc.applicationId}")
    print(f"Tracking URL: {sc.uiWebUrl}")

    # Forcer un petit job
    spark.table(f"{HIVE_DB}.{HIVE_TABLE}").limit(1).count()

    # Chargement et transformation
    df = spark.table(f"{HIVE_DB}.{HIVE_TABLE}")
    df = df.withColumn("use_chip_bool",
                       F.when(F.lower(F.col("use_chip")).contains("chip"), 1).otherwise(0))

    # Calcul des poids pour gérer le déséquilibre des classes
    total = df.count()
    count_0 = df.filter(F.col("label") == 0).count()
    count_1 = df.filter(F.col("label") == 1).count()
    weight_0 = total / (2.0 * count_0)
    weight_1 = total / (2.0 * count_1)
    df = df.withColumn("weight", F.when(F.col("label") == 0, weight_0).otherwise(weight_1))

    cat_cols = ["card_brand", "card_type", "merchant_state"]
    num_cols = ["amount", "use_chip_bool", "credit_limit", "per_capita_income",
                "yearly_income", "total_debt", "credit_score", "num_credit_cards"]

    train, test = df.randomSplit([0.8, 0.2], seed=42)
    evaluator_auc = BinaryClassificationEvaluator(labelCol="label", rawPredictionCol="rawPrediction", metricName="areaUnderROC")
    evaluator_acc = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName="accuracy")

    experiments = [
        ("LR", LogisticRegression(labelCol="label", featuresCol="features", weightCol="weight", maxIter=100, regParam=0.0)),
        ("RF", RandomForestClassifier(labelCol="label", featuresCol="features", weightCol="weight", numTrees=100, maxDepth=10)),
        ("GBT", GBTClassifier(labelCol="label", featuresCol="features", weightCol="weight", maxIter=100, maxDepth=5))
    ]

    results = []
    for name, model in experiments:
        with mlflow.start_run(run_name=name):
            for p, v in model.extractParamMap().items():
                mlflow.log_param(p.name, v)
            pipeline = Pipeline(stages=prep_pipeline(cat_cols, num_cols) + [model])
            fitted = pipeline.fit(train)
            preds = fitted.transform(test)
            auc = evaluator_auc.evaluate(preds)
            accuracy = evaluator_acc.evaluate(preds)

            # Calculer précision, rappel et F1-score
            tp = preds.filter(F.col("label") == 1).filter(F.col("prediction") == 1).count()
            fp = preds.filter(F.col("label") == 0).filter(F.col("prediction") == 1).count()
            fn = preds.filter(F.col("label") == 1).filter(F.col("prediction") == 0).count()
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            mlflow.log_metric("test_auc", auc)
            mlflow.log_metric("accuracy", accuracy)
            mlflow.log_metric("precision", precision)
            mlflow.log_metric("recall", recall)
            mlflow.log_metric("f1_score", f1)
            mlflow.spark.log_model(fitted, artifact_path="model")
            results.append((name, auc, mlflow.active_run().info.run_id))

    names, aucs, run_ids = zip(*results)
    plt.figure()
    plt.bar(names, aucs)
    plt.ylabel("AUC")
    plt.title("Comparaison AUC modèles")
    plt.tight_layout()
    plt.savefig("auc_comparison.png")
    mlflow.log_artifact("auc_comparison.png")

    best_run = run_ids[aucs.index(max(aucs))]
    mlflow.register_model(f"runs:/{best_run}/model", name="BestFraudModel")

    # Télécharger et sauvegarder le meilleur modèle
    client = MlflowClient()
    local_artifact_dir = client.download_artifacts(run_id=best_run, path="model")
    print(f"📥 Downloaded run {best_run} model artifacts to {local_artifact_dir}")
    sparkml_folder = os.path.join(local_artifact_dir, "sparkml")
    local_uri = f"file://{sparkml_folder}"
    print(f"🚀 Loading Spark pipeline from local URI {local_uri} …")
    spark_model = PipelineModel.load(local_uri)

    local_path = Path(__file__).parent / "fraud_model_mlflow"
    mlflow.spark.save_model(spark_model, path=str(local_path))
    print(f"✅ Spark pipeline saved to {local_path}")

    class SparkModelWrapper:
        def __init__(self, model_dir: str):
            self._model_dir = model_dir
        def predict(self, spark_df):
            from pyspark.ml import PipelineModel
            return PipelineModel.load(self._model_dir).transform(spark_df)

    wrapper = SparkModelWrapper(str(local_path))
    output_path = Path(__file__).parent / "fraud_logreg.pkl"
    with open(output_path, "wb") as f:
        cloudpickle.dump(wrapper, f)
    print(f"✅ Pickled wrapper to {output_path}")

    if watcher_pid:
        from signals import ML_SIG_DONE
        os.kill(watcher_pid, ML_SIG_DONE)
    sys.exit(0)

if __name__ == "__main__":
    main()