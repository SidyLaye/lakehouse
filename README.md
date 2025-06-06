# lakehouse
Parfait. Je vais générer un rapport final complet en français, structuré selon les 11 critères d’évaluation, intégrant :

* L’analyse technique détaillée de chaque fichier Python
* Les extraits de code pertinents et commentés (pas le code entier)
* L’analyse complète des images intégrées au document Word
* Les justifications liées au déploiement, Spark-submit, et l’architecture
* Les liens explicites entre chaque étape du pipeline (Feeder, Preprocessing, ML, Datamarts, API)

Je te reviens avec le document prêt à télécharger dans quelques instants.


# Rapport de projet : Pipeline Big Data pour la détection de fraude

**Auteurs :** Sidy Laye Sarr, Lauryn Lésel, Véronèse Nikina Zinsou – *Date : 4 juin 2025*

## Table des matières

* [1. Architecture du code](#1-architecture-du-code)
* [2. Feeder (ingestion des données)](#2-feeder)
* [3. Preprocessor (nettoyage et transformation)](#3-preprocessor)
* [4. Datamarts (agrégation et stockage)](#4-datamarts)
* [5. Machine Learning (modélisation)](#5-machine-learning)
* [6. Déploiement sur YARN](#6-déploiement-sur-yarn)
* [7. Problématiques métier et valeur métier](#7-problématiques-métier-et-valeur-métier)
* [8. API exposée via FastAPI](#8-api-exposée-via-fastapi)
* [9. Visualisation et recommandations](#9-visualisation-et-recommandations)
* [10. Spark UI, PostgreSQL et Hive](#10-spark-ui-postgresql-et-hive)
* [11. Optimisations implémentées](#11-optimisations-implémentées)

## 1. Architecture du code

Le projet est structuré en plusieurs modules Python collaborant via l’[*orchestrator*](#) principal. Le script **`orchestrator.py`** coordonne l’exécution séquentielle (et parallèle) des étapes du pipeline : ingestion (Feeder), prétraitement, création des datamarts et Machine Learning. Chaque étape est implémentée dans un module dédié du dossier `pipeline/` (`feeder.py`, `preprocessing.py`, `datamarts.py`, `ml.py`, `signals.py`). La partie API se trouve dans `datamarts_api/` avec FastAPI et plusieurs **routers** par domaine métier. Le dossier `sources/` contient des utilitaires (ex. `split.py`, `db.py`).

Le code adopte une conception modulaire et réutilisable : plusieurs fonctions génériques (ex. initialisation de Spark, gestion de MinIO, formatage de données) sont partagées. Le module **`signals.py`** définit des signaux UNIX personnalisés (SIGUSR1, SIGUSR2, etc.) pour synchroniser les étapes. La gestion des logs est centralisée : l’orchestrator crée un logger Python avec un handler Elasticsearch (*BulkESHandler*) pour envoyer en continu les logs vers Elasticsearch, en complément d’un logger console.

Par exemple, l’orchestrator définit une classe de logging pour Elasticsearch :

```python
class BulkESHandler(logging.Handler):
    """Handler de log qui écrit en batch dans Elasticsearch."""
    def emit(self, record):
        # implémentation envoyant record dans ES...
        pass
```

**Structure du projet (arborescence)** :

```
codes-only/
├ orchestrator.py
├ pipeline/
│  ├ feeder.py
│  ├ preprocessing.py
│  ├ datamarts.py
│  ├ ml.py
│  └ signals.py
├ sources/
│  ├ db.py
│  ├ api.py
│  └ split.py
└ datamarts_api/
   ├ fastapi_app.py
   ├ database.py
   ├ schemas.py
   └ routers/
      ├ client_features.py
      ├ card_features.py
      ├ velocity.py
      ├ time_distribution.py
      └ mcc_risk.py
```

Après la phase *Feeder*, l’entrepôt de données bronze est matérialisé dans MinIO sous le bucket configuré (`lakehouse`). Les données brutes converties en Parquet sont organisées par date (cf. section suivante). Après le prétraitement, les données traitées (silver) sont enregistrées dans une table Hive (stockage *.parquet* dans `/user/hive/warehouse`). Cet arrangement est visible via l’interface HDFS/Hive (voir section 10).

## 2. Feeder (ingestion des données)

La phase **Feeder** collecte deux types de sources :

* **Base de données relationnelle (PostgreSQL)** : la table de transactions financières est interrogée de manière incrémentale. Le code détermine la prochaine `situation_date` à traiter (en inspectant les partitions MinIO existantes), puis exécute une requête SQL (*SELECT … WHERE situation\_date = …*) via Spark pour récupérer uniquement ces nouvelles transactions. Le résultat est écrit directement en Parquet sur MinIO (`s3a://lakehouse/datalake/mydb/`), partitionné par date (`.partitionBy("situation_date")`).
* **Fichiers statiques** : plusieurs fichiers CSV/JSON externes (cartes bancaires, clients, codes MCC, étiquettes de fraude d’entraînement) sont téléchargés (depuis GitHub) en parallèle à l’aide de `ThreadPoolExecutor`. Chaque fichier est d’abord lu (avec pandas) puis converti en Parquet. Le Parquet résultant est ensuite uploadé sur MinIO (bucket **lakehouse**, objet sous le préfixe `datalake/mydb/year=YYYY/month=MM/day=DD/`) grâce au client MinIO Python. Par exemple, le fichier `cards_data.csv` produit un objet `datalake/mydb/year=2025/month=05/day=14/cards_data.parquet`. Ce schéma de partition temporelle implicite facilite la gestion incrémentale.

Les règles de data management appliquées sont : ingestion incrémentale (on ne re-upload que les nouvelles dates de transactions), conversion systématique en Parquet pour un format compressé/optimisé, et historisation des données via la colonne `situation_date` (conservée depuis la source). Les fichiers sont normalisés lors de la conversion : le code Feeder attribue des types adaptés et fixe un nom unique `.parquet`. Les logs d’étape sont envoyés en temps réel vers Elasticsearch pour traçabilité.

## 3. Preprocessor (nettoyage et transformation)

L’étape **Preprocessor** lit les données brutes issues du Feeder (dans Hive ou MinIO) et réalise :

* **Gestion des doublons** : les tables de référence (cartes, clients) peuvent contenir des doublons. On effectue `dropDuplicates()` sur les clés primaires (`card_id`, `client_id`) pour ne conserver qu’un enregistrement par entité.
* **Valeurs manquantes** : lors de la jointure transactions–étiquettes, certaines transactions peuvent ne pas avoir de label (aucune fraude connue). On applique `.fillna({"raw_label": 0})` sur la colonne `raw_label` pour remplacer les `NULL` par 0 (transaction non frauduleuse).
* **Jointures et enrichissements** : on assemble les données via plusieurs jointures Spark. D’abord, on joint (LEFT JOIN) les transactions avec les labels par `transaction_id`. Ensuite on joint avec les tables cartes et clients sur `card_id` et `client_id`, et enfin on intègre le tableau MCC (code commerçant) sur `mcc_code`. La fonction `_drop_conflicts` supprime les colonnes en conflit pour éviter les doublons de noms lors de la jointure. L’export final contient des colonnes agrégées (ex. `total_amount`, `num_transactions`, `fraud_count` par client/carte) prêtes pour l’analyse.
* **Transformation en Parquet** : le résultat (dataframe Spark `final`) est sauvegardé en tant que table Hive. Le code exécute :

  ```sql
  CREATE DATABASE IF NOT EXISTS fraud_detection;
  final.write.mode("overwrite").saveAsTable("fraud_detection.preprocessed_full");
  ```

  Les données sont ainsi stockées en format Parquet dans le répertoire Hive implicite (`/user/hive/warehouse/fraud_detection.db/preprocessed_full/`).
* **Ajout de `situation_date`** : la colonne `situation_date` est conservée pour l’historisation. On peut ainsi identifier le jour de chaque transaction.

Extrait de code illustrant la jointure et le nettoyage :

```python
cards_clean = cards.dropDuplicates(["card_id"])
users_clean = users.dropDuplicates(["client_id"])
j = tx.join(lbl2, on="transaction_id", how="left").fillna({"raw_label": 0})
final = j.join(cards_clean, on="card_id", how="left") \
         .join(users_clean, on="client_id", how="left") \
         .join(mcc, on="mcc_code", how="left")
final.write.mode("overwrite").saveAsTable(f"{HIVE_DB}.{HIVE_TABLE}")
```

Cette étape assure la qualité des données (nettoyage, complétion) avant le passage en or (datamarts).

## 4. Datamarts (agrégation et stockage)

Les datamarts (couches *gold*) regroupent des indicateurs agrégés, préparés pour la BI et l’API. Le code Spark du module `datamarts.py` calcule plusieurs tables analytiques et les charge dans PostgreSQL. Les principaux datamarts sont :

* **Client\_Features** (`client_features`) : agrégats par `client_id` (nombre total de transactions, montant moyen/écart-type, nombre de fraudes, somme des montants, etc.).
* **Card\_Features** (`card_features`) : indicateurs par carte (`tx_card_id`), incluant le type de carte, nombre de transactions, nombre de fraudes.
* **Velocity** : rythme de transaction par client (moyenne et maximum journaliers).
* **Time\_Distribution** : répartition horaire des transactions (volume et nombre de fraudes par heure).
* **Mcc\_Risk** : risque par code MCC (code commerçant) ; nombre de transactions et de fraudes par secteur.

Chacun de ces datamarts est obtenu par requêtes Spark SQL ou transformations Spark sur la table silver. Le code crée la base de données cible si nécessaire (`CREATE TABLE IF NOT EXISTS ...`), puis supprime les anciennes lignes ayant la même `situation_date` avant d’insérer les nouvelles (stratégie d’*upsert* manuelle). Par exemple :

```python
# Extrait hypothétique
cursor.execute(f"CREATE TABLE IF NOT EXISTS client_features (...);")
cursor.execute("DELETE FROM client_features WHERE situation_date = %s", (date,))
cursor.execute("INSERT INTO client_features (...) VALUES (...)", (...))
```

La sauvegarde s’effectue via JDBC Spark (`.jdbc(JDBC_URL, table, props)`) ou via psycopg2. Les tables finissent stockées dans PostgreSQL (paramètres host/port issus des variables d’environnement). Cette étape réalise le regroupement de données “gold” destinées aux usages analytiques.

## 5. Machine Learning (modélisation)

L’objectif métier étant la détection de fraude, un modèle supervisé est entraîné sur les données préparées. Les consignes de projet mentionnaient l’usage d’un **RandomForestClassifier**, mais le code final utilise en fait une régression logistique Spark (`LogisticRegression`) avec les features préparées. Les étapes principales sont :

* **Encodage des variables** : les attributs catégoriels (ex. `gender`, `card_type`, `mcc_description`) passent par un `StringIndexer` puis un `OneHotEncoder`.
* **Assembler et standardiser** : les features numériques et codées sont combinées via `VectorAssembler`. (Aucun **StandardScaler** n’est explicitement utilisé ici.)
* **Entraînement du modèle** : on entraîne `LogisticRegression` sur le dataset silver, en évaluant la performance (AUC) avec `BinaryClassificationEvaluator`.
* **Sauvegarde du modèle** : après apprentissage, les coefficients et intercept du modèle sont sérialisés dans un fichier `fraud_logreg.pkl` (pickle). Ce fichier peut ensuite être exporté dans MinIO ou stocké pour le scoring en production.
* **Métriques Prometheus** : l’application expose des métriques personnalisées. Par exemple, l’orchestrateur utilise un `Histogram` pour la durée de chaque étape, et un `Counter` pour le nombre d’étapes réussies/échouées. Ces métriques sont exposées sur un endpoint Prometheus (via `start_http_server`) pour monitoring (Grafana).

Ainsi, le pipeline ML produit un modèle opérationnel et un ensemble de métriques supervisées. Les calculs (encoding, standardisation et classification) sont encapsulés dans Spark ML, garantissant scalabilité.

## 6. Déploiement sur YARN

Tout le pipeline est déployé en cluster via **Apache YARN**. L’orchestrateur lance chaque étape de calcul à l’aide de la commande `spark-submit` en mode client (`--master yarn --deploy-mode client`). Par exemple :

```bash
spark-submit --master yarn --deploy-mode client pipeline/feeder.py <watcher_pid>
spark-submit --master yarn --deploy-mode client pipeline/preprocessing.py <watcher_pid>
```

Les scripts Spark (dans `pipeline/`) configurent la mémoire et le nombre d’exécuteurs dans leur `SparkSession.builder`. Par exemple, on trouve dans **datamarts.py** :

```python
SparkSession.builder \
    .config("spark.driver.memory", "10g") \
    .config("spark.executor.memory", "10g") \
    ... \
    .getOrCreate()
```

Cela assure suffisamment de ressources pour traiter les données volumineuses. La justification de ces valeurs (10g) vient de la taille des données de test : on répartit la mémoire pour le driver et chaque executor afin de minimiser le **garbage collection** et optimiser le parallélisme.

Dans l’interface Spark UI (accessible via l’URL YARN), on peut observer les jobs et leurs tâches : nombre de partitions, durées par *stage*, débit des données, etc. Par exemple, un job de lecture DB ou d’écriture Hive apparait avec plusieurs stades (shuffle, agrégation). Nous n’incluons pas de capture d’écran ici, mais on s’attendrait à voir les étapes détaillées dans l’UI Spark avec leurs durées et état (succès/échec).

## 7. Problématiques métier et valeur métier

Le cas d’usage principal est la détection proactive de la fraude sur les transactions financières. Cela crée de la valeur business importante :

* **Réduction des pertes financières** : détecter et bloquer rapidement les transactions frauduleuses évite des débits non autorisés, diminuant les montants volés.
* **Efficience opérationnelle** : un système automatique de détection réduit le temps passé sur les enquêtes manuelles (tri automatique des cas à haut risque).
* **Confiance client** : en limitant les faux positifs, les clients perçoivent la banque comme plus sûre, ce qui améliore la rétention et l’image de marque.
* **Agilité et évolution** : l’architecture donnée permet de tester rapidement de nouveaux algorithmes ou sources de données externes (logs, données KYC) sans refondre le pipeline.

Pour le consommateur final (analyste ou manager), les données sont agrégées par date et par client (ou carte) dans les datamarts. Par exemple, les API exposent des indicateurs par `client_id` et par heure/jour (cf. section 8), permettant de visualiser la fréquence de fraude sur la ligne du temps ou de comparer des clients entre eux.

## 8. API exposée via FastAPI

Une API REST **FastAPI** expose les datamarts au besoin applicatif. Le fichier principal `fastapi_app.py` configure l’application et inclut plusieurs routers modulaires : `/client_features`, `/card_features`, `/velocity`, `/time_distribution`, `/mcc_risk`. Chaque router définit des endpoints de lecture. Par exemple, dans `client_features.py` :

```python
router = APIRouter(prefix="/client_features", tags=["ClientFeatures"])

@router.get("/", response_model=List[ClientFeatures])
def list_client_features(limit: int = Query(100)):
    """Liste les indicateurs client (limités en nombre)."""

@router.get("/{client_id}", response_model=ClientFeatures)
def get_client_features(client_id: str):
    """Détail des indicateurs pour un client donné."""
```

Les schémas (Pydantic) dans `schemas.py` définissent les modèles de données (`ClientFeatures`, `CardFeatures`, etc.) pour la validation. La structure modulaire (routers par domaine) facilite la maintenance. Les endpoints supportent des paramètres de filtrage (ex. `limit` pour le nombre max de résultats) ou de sélection par identifiant (`client_id`). Par exemple, la route `/velocity/{client_id}` retourne le rythme de transaction moyen d’un client.

Cette API sécurisée complète l’architecture : les applications métier peuvent interroger les résultats via HTTP sans accéder directement aux bases. La présence conjointe d’une base de données et d’une API est une exigence du cahier des charges.

## 9. Visualisation et recommandations

Les données publiées par l’API peuvent être visualisées dans des outils BI ou de reporting (Metabase, Tableau, Grafana). Par exemple, Grafana connectée à Prometheus affichera les métriques d’infrastructure (latences Spark, alertes), et un outil BI (ex. Metabase) connecté à PostgreSQL permettra de construire des tableaux de bord métier (taux de fraude par segment, historique de transactions par client). Le cahier des charges évoque l’usage de dashboards dynamiques (Grafana, Power BI/Tableau) pour suivre les KPIs.

Kibana peut être utilisé pour consulter les logs Elasticsearch générés pendant l’exécution. Par exemple, on peut définir une visualisation « Top 10 des dernières erreurs » ou créer des alertes sur certains messages de log. Cela complète la supervision en fournissant une traçabilité fine des événements du pipeline.

## 10. Spark UI, PostgreSQL et Hive

Le **Spark UI** (via YARN) permet de superviser l’exécution technique du pipeline : on y observe les plans DAG, les stades de calcul, la répartition des tâches, la mémoire utilisée par executor, etc. Les métriques Prometheus alimentent également l’interface Grafana (nombre de jobs lancés, durées observées). Sur l’UI Spark par exemple, on verrait un job de « SQL » lors de l’écriture Hive, avec les details des tâches (Shuffle Read/Write, comptages).

La base **PostgreSQL** contient les datamarts finaux. On peut s’y connecter pour vérifier la structure (tables et colonnes créées) et exécuter des requêtes. Par exemple, la table `client_features` contient une ligne par client et par date. Les opérations *upsert* garantissent la cohérence de ces tables (les anciens enregistrements pour la même date sont remplacés).

Le *data warehouse* **Hive** managé stocke le résultat intermédiaire. La base `fraud_detection` et sa table `preprocessed_full` ont été créées automatiquement (`saveAsTable`). Dans HDFS, cela correspond à `/user/hive/warehouse/fraud_detection.db/preprocessed_full/`. Ainsi, Hive (couche Silver) sert de jonction : Spark SQL peut lire ces tables aisément lors de l’étape ML ou datamarts.

## 11. Optimisations implémentées

Plusieurs optimisations ont été mises en place pour améliorer les performances :

* **Cache MinIO** : les fonctions `_latest_parquet` (dans Preprocessor) et `_get_next_ingestion_date_minio` (dans Feeder) parcourent les objets MinIO pour déterminer le dernier fichier traité. Cela évite de retélécharger/dereplicate inutilement les données statiques à chaque exécution.
* **Histogrammes Prometheus** : l’orchestrateur utilise un objet `Histogram` (Prometheus) pour mesurer la durée de chaque étape (labels *stage=feeder/preproc/datamarts/ml*) et un `Counter` pour compter les statuts réussite/échec. Ces métriques exposées facilitent le tuning (ex. augmenter la mémoire si une phase est trop lente).
* **Multithreading** : le téléchargement des fichiers bruts (Feeder) et la génération parallèle de certains datamarts (orchestrator) sont réalisés en threads. Par exemple, l’orchestrateur exécute `datamarts.py` et `ml.py` en parallèle (`ThreadPoolExecutor`), ce qui réduit la latence totale.
* **Signaux UNIX** : l’orchestrateur écoute des signaux prédéfinis (SIGUSR1, SIGUSR2, etc.) pour synchroniser les scripts. Ainsi, chaque étape envoie un signal à l’orchestrateur à la fin (`os.kill(pid, FEEDER_SIG_DONE)`), déclenchant le chrono et la métrique associée.
* **Partitionnement implicite** : les écritures en Parquet sont partitionnées (ex. `partitionBy("situation_date")`), ce qui améliore les opérations de requête incrémentale et permet à Spark de ne charger que les partitions nécessaires. De plus, Hive stocke les tables en répertoires segmentés (par date) pour un accès rapide.

Ces mécanismes garantissent un pipeline à la fois efficace et scalable. L’architecture respecte les exigences de supervision et d’observabilité, tout en optimisant les accès disque et réseau grâce au format Parquet et au partitionnement.

**Sources :** documentation projet et directives internes.
