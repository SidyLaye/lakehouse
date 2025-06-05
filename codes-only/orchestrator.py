#!/usr/bin/env python3
import os
import sys
import logging
import threading
import time
import atexit
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from prometheus_client import start_http_server, Counter, Histogram
import smtplib
import ssl
from email.mime.text import MIMEText

# 1) Import Elasticsearch AVANT tout réglage de logging
from elasticsearch import Elasticsearch, exceptions as es_exceptions, helpers

# --- Configuration globale -------------------------
SPARK_MASTER = os.getenv("SPARK_MASTER", "yarn")
SMTP_HOST    = os.getenv('SMTP_HOST',  'smtp.gmail.com')
SMTP_PORT    = int(os.getenv('SMTP_PORT',  '587'))
SMTP_USER    = os.getenv('SMTP_USER',  'votre.email@gmail.com')
SMTP_PASS    = os.getenv('SMTP_PASS',  'votre_mdp')
ALERT_EMAIL  = os.getenv('ALERT_EMAIL', SMTP_USER)

_raw_es_host = os.getenv('ES_HOST', 'http://localhost:9200')
if _raw_es_host.startswith("https://"):
    ES_HOST = _raw_es_host.replace("https://", "http://", 1)
else:
    ES_HOST = _raw_es_host

ES_INDEX     = os.getenv('ES_INDEX',   'pipeline-logs')
ES_BULK_SIZE = int(os.getenv('ES_BULK_SIZE', '100'))
ES_FLUSH_INT = int(os.getenv('ES_FLUSH_INTERVAL', '5'))
PROM_PORT    = int(os.getenv('PROM_PORT',   '8000'))

# --- Logging console (handler de base) ---------------
root = logging.getLogger()
root.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s'))
root.addHandler(console_handler)

# Ce logger « orchestrator » pour la suite
logger = logging.getLogger('orchestrator')
logger.propagate = True   # remonte vers root→console


# --- BulkESHandler corrigé (RLock + masquage des logs ES pendant bulk) -------------
class BulkESHandler(logging.Handler):
    """
    Handler qui bufferise les logs et les envoie en bulk vers Elasticsearch.
    On utilise un RLock pour éviter les deadlocks si, pendant un helpers.bulk(),
    la lib ES produit un log qui ré-appelle emit() dans le même thread.
    """
    def __init__(self, index_name,
                 bulk_size=ES_BULK_SIZE,
                 flush_interval=ES_FLUSH_INT,
                 max_retries=3,
                 backoff_factor=1):
        super().__init__()
        self.index_name     = index_name
        self.bulk_size      = bulk_size
        self.flush_interval = flush_interval
        self.max_retries    = max_retries
        self.backoff_factor = backoff_factor
        self.actions        = []
        # → On met un RLock, pas un Lock
        self.lock           = threading.RLock()
        self.es             = None

        # On masque temporairement les loggers ES (level WARNING)
        es_logger = logging.getLogger('elasticsearch')
        et_logger = logging.getLogger('elastic_transport.transport')
        prev_es_level = es_logger.level
        prev_et_level = et_logger.level
        es_logger.setLevel(logging.WARNING)
        et_logger.setLevel(logging.WARNING)

        try:
            self.es = Elasticsearch(
                [ES_HOST],
                request_timeout=1,            # remplace ‘timeout’ en v9.x
                sniff_on_node_failure=False,
                max_retries=0
            )
        except Exception as ex:
            logging.getLogger(__name__).warning(
                f"⚠︎ Échec création client Elasticsearch ({ES_HOST}) : {ex}"
            )
            self.es = None

        if self.es:
            try:
                if not self.es.ping():
                    logging.getLogger(__name__).warning(
                        f"⚠︎ Ping ES échoué ({ES_HOST})"
                    )
            except Exception:
                pass

        # On restaure immédiatement le niveau d’avant
        es_logger.setLevel(prev_es_level)
        et_logger.setLevel(prev_et_level)

        # Thread périodique d’envoi (daemon)
        t = threading.Thread(target=self._flush_periodically, daemon=True)
        t.start()

    def emit(self, record):
        if not self.es:
            # ES indisponible → on ignore
            sys.stderr.write("[BulkESHandler] ES indispo : log ignoré\n")
            return

        entry = {
            '@timestamp': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(record.created)),
            'level':       record.levelname,
            'message':     record.getMessage(),
            'logger':      record.name,
        }
        action = {"_index": self.index_name, "_source": entry}

        # → Avec RLock, même si le même thread tient déjà le verrou (pendant _flush),
        #   il pourra le ré-acquérir ici sans se bloquer.
        with self.lock:
            self.actions.append(action)
            if len(self.actions) >= self.bulk_size:
                self._flush()

    def _flush_periodically(self):
        while True:
            time.sleep(self.flush_interval)
            with self.lock:
                if self.actions:
                    self._flush()

    def _flush(self):
        """
        Extrait le buffer, puis lance helpers.bulk() **en masquant** les loggers ES
        afin que tout log interne ne déclenche pas emit() verrouillé.
        """
        actions, self.actions = self.actions, []
        if not self.es:
            return

        es_logger = logging.getLogger('elasticsearch')
        et_logger = logging.getLogger('elastic_transport.transport')
        prev_es_level = es_logger.level
        prev_et_level = et_logger.level
        es_logger.setLevel(logging.WARNING)
        et_logger.setLevel(logging.WARNING)

        for attempt in range(self.max_retries + 1):
            try:
                helpers.bulk(self.es, actions)
                break
            except es_exceptions.TransportError as e:
                # 429 Too Many Requests → backoff exponentiel
                if getattr(e, 'status_code', None) == 429:
                    time.sleep(self.backoff_factor * (2 ** attempt))
                    continue
                else:
                    break
            except Exception as e:
                logging.getLogger(__name__).warning(f"[BulkESHandler] Bulk ES échoué : {e}")
                break

        # On restaure les niveaux initiaux des loggers ES
        es_logger.setLevel(prev_es_level)
        et_logger.setLevel(prev_et_level)

        if attempt == self.max_retries:
            sys.stderr.write(f"WARNING: {len(actions)} logs abandonnés après erreur ES\n")

    def flush_remaining(self):
        # Envoi final des logs restants (via atexit)
        with self.lock:
            if self.actions:
                self._flush()


# --- Instanciation du handler ES (sans l’attacher tout de suite) -------------
bulk_handler = BulkESHandler(ES_INDEX)
atexit.register(bulk_handler.flush_remaining)


# --- SMTP et alertes email ------------------------
alerts_enabled = True
if not (SMTP_USER and SMTP_PASS and ALERT_EMAIL):
    logger.warning("❗ SMTP non configuré ; désactivation des alertes email.")
    alerts_enabled = False

def send_alert(subject: str, body: str):
    if not alerts_enabled:
        logger.warning(f"Impossible d'envoyer l'alerte '{subject}' : SMTP indisponible.")
        return
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From']    = SMTP_USER
    msg['To']      = ALERT_EMAIL
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        logger.warning(f"SMTP auth error : {e}")
    except Exception as e:
        logger.warning(f"SMTP send error : {e}")


# --- Prometheus metrics ---------------------------
STAGE_DURATION = Histogram('pipeline_stage_duration_seconds',
                           'Durée (s) de chaque étape du pipeline', ['stage'])
STAGE_STATUS   = Counter('pipeline_stage_status_total',
                         "Nombre d'états (démarrée, succès, échec) par étape", ['stage', 'status'])


# --- Signal handling ------------------------------
from pipeline.signals import (
    FEEDER_SIG_CARD,
    FEEDER_SIG_USER,
    FEEDER_SIG_MCC,
    FEEDER_SIG_LABELS,
    FEEDER_SIG_DB,
    FEEDER_SIG_DONE,
    PREPROC_SIG_RAW,
    PREPROC_SIG_DB,
    PREPROC_SIG_DONE,
    DM_SIG_CLIENT_FEATURES,
    DM_SIG_CARD_FEATURES,
    DM_SIG_VELOCITY,
    DM_SIG_MCC_RISK,
    DM_SIG_TIME_DISTRIBUTION,
    DM_SIG_DONE,
    ML_SIG_DONE,
    print_signal_mapping
)

watcher_pid = os.getpid()
start_times = {}

signal_to_stage = {
    FEEDER_SIG_DONE:    'feeder',
    PREPROC_SIG_DONE:   'preprocessing',
    DM_SIG_DONE:        'datamarts',
    ML_SIG_DONE:        'ml',
}

def _on_stage_done(signum, frame):
    stage = signal_to_stage.get(signum, '?')
    end   = time.time()
    start = start_times.get(stage, end)
    STAGE_DURATION.labels(stage=stage).observe(end - start)
    STAGE_STATUS.labels(stage=stage, status='success').inc()
    logger.info(f"Stage «{stage}» terminée en {(end - start):.1f}s (signal={signum})")

for sig in signal_to_stage:
    signal.signal(sig, _on_stage_done)

def _ignore_intermediate(signum, frame):
    logger.info(f"[orchestrator] Ignoré signal intermédiaire : {signum}")

ignore_signals = [
    FEEDER_SIG_CARD, FEEDER_SIG_USER, FEEDER_SIG_MCC, FEEDER_SIG_LABELS,
    FEEDER_SIG_DB,
    PREPROC_SIG_RAW, PREPROC_SIG_DB,
    DM_SIG_CLIENT_FEATURES, DM_SIG_CARD_FEATURES,
    DM_SIG_VELOCITY, DM_SIG_MCC_RISK, DM_SIG_TIME_DISTRIBUTION,
]
for sig in ignore_signals:
    signal.signal(sig, _ignore_intermediate)


# --- Fonction pour lancer une étape Spark -------------
def run_stage(stage: str, script: str, extra_args=None):
    cmd = [
        'spark-submit', '--master', SPARK_MASTER, '--deploy-mode', 'client',
        script, str(watcher_pid)
    ]
    if extra_args:
        cmd += extra_args

    logger.info(f"→ Lancement étape «{stage}» : {' '.join(cmd)}")
    start_times[stage] = time.time()
    STAGE_STATUS.labels(stage=stage, status='started').inc()

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True
    )
    for line in proc.stdout:
        logger.info(f"[{stage}] {line.rstrip()}")

    ret = proc.wait()
    if ret != 0:
        STAGE_STATUS.labels(stage=stage, status='failure').inc()
        msg = f"Étape «{stage}» échouée (code {ret})"
        logger.error(msg)
        send_alert(f"[ALERTE] pipeline : {stage} échoué", msg)
        sys.exit(ret)


# --- Programme principal -----------------------------
if __name__ == '__main__':
    # 1) Affichage console initial (avant attachement du handler ES)
    logger.info(f"ES_HOST={ES_HOST}, ES_INDEX={ES_INDEX}, BULK_SIZE={ES_BULK_SIZE}, FLUSH_INTERVAL={ES_FLUSH_INT}s")
    logger.info(f"SMTP_HOST={SMTP_HOST}, SMTP_USER={'défini' if SMTP_USER else 'non défini'}")
    logger.info(f"Prometheus écoute sur :{PROM_PORT}, Spark master={SPARK_MASTER}")
    logger.info("Serveur Prometheus démarré")

    # 2) ↴ Maintenant que tous les logs initiaux sont envoyés en console,
    #    on attache enfin le handler Elasticsearch.
    root.addHandler(bulk_handler)

    # 3) Démarrage non bloquant du serveur Prometheus
    start_http_server(PROM_PORT)

    # 4) Étapes séquentielles (feeder → preprocessing)
    sequential_stages = [
        ('feeder',        'pipeline/feeder.py'),
        ('preprocessing', 'pipeline/preprocessing.py'),
    ]
    for name, script in sequential_stages:
        run_stage(name, script)

    # 5) Étapes parallèles (datamarts & ml)
    parallel_stages = [
        ('datamarts', 'pipeline/datamarts.py'),
        ('ml',        'pipeline/ml.py'),
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(run_stage, name, script): name
            for name, script in parallel_stages
        }
        for fut in as_completed(futures):
            fut.result()

    logger.info("🎉 Tout le pipeline a réussi !")
    send_alert("Pipeline réussi", "Toutes les étapes se sont terminées sans erreur.")
    sys.exit(0)
