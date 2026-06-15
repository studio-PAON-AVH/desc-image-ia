"""Métriques métier du pipeline de description d'EPUB.

Les instruments sont créés via l'API globale OTel : tant que
setup_observability n'a pas été appelé ils sont no-op (proxys), ensuite ils
sont re-liés au vrai MeterProvider et exportés en OTLP vers Mimir.
"""

import logging

from opentelemetry import metrics

logger = logging.getLogger(__name__)

meter = metrics.get_meter("desc-image-ia")

# --- API : upload d'EPUB ---

epub_upload_counter = meter.create_counter(
    "epub.upload",
    description="Uploads d'EPUB, par statut (accepted/rejected) et raison de rejet",
    unit="1",
)

epub_upload_size = meter.create_histogram(
    "epub.upload.size",
    description="Taille des fichiers EPUB acceptés",
    unit="By",
    explicit_bucket_boundaries_advisory=[
        100_000, 1_000_000, 5_000_000, 10_000_000, 25_000_000, 50_000_000, 100_000_000
    ],
)

# --- Worker : tâches de description ---

epub_images_per_file = meter.create_histogram(
    "epub.images.per_file",
    description="Nombre d'images extraites par EPUB",
    unit="1",
    explicit_bucket_boundaries_advisory=[1, 5, 10, 25, 50, 100, 250, 500],
)

task_counter = meter.create_counter(
    "task.processed",
    description="Tâches de description terminées, par statut (completed/failed)",
    unit="1",
)

task_duration = meter.create_histogram(
    "task.duration",
    description="Durée totale de traitement d'un EPUB, par statut",
    unit="s",
    explicit_bucket_boundaries_advisory=[1, 5, 15, 30, 60, 120, 300, 600, 1800],
)

# EPUB en cours de traitement dans le worker (gauge non-monotone). Révèle la
# concurrence réelle : taskiq retire les tâches de la queue Redis aussitôt
# (worker.queue.depth reste ~0), elles s'accumulent ici, en vol dans l'event loop.
worker_tasks_in_flight = meter.create_up_down_counter(
    "worker.tasks.in_flight",
    description="EPUB en cours de traitement dans le worker",
    unit="1",
)

# --- Appels aux modèles IA ---

ai_call_duration = meter.create_histogram(
    "ai.call.duration",
    description="Durée d'un appel batch à un modèle IA, par modèle",
    unit="s",
    explicit_bucket_boundaries_advisory=[0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300],
)

ai_call_errors = meter.create_counter(
    "ai.call.errors",
    description="Appels batch à un modèle IA en échec, par modèle",
    unit="1",
)

# Le vrai backlog : avec MAX_CONCURRENT_PER_MODEL=1 et des modèles qui traitent
# une image à la fois, les requêtes s'empilent derrière le sémaphore de chaque
# modèle. C'est cette file (et pas la queue Redis) qui mesure la saturation.
ai_call_waiting = meter.create_up_down_counter(
    "ai.call.waiting",
    description="Requêtes bloquées en attente du sémaphore, par modèle",
    unit="1",
)

ai_call_in_flight = meter.create_up_down_counter(
    "ai.call.in_flight",
    description="Requêtes en cours d'exécution, par modèle",
    unit="1",
)

# Temps passé à attendre le sémaphore avant l'appel : latence cachée que
# ai.call.duration ignore (son chrono ne démarre qu'après l'acquisition).
ai_call_wait = meter.create_histogram(
    "ai.call.wait",
    description="Temps d'attente du sémaphore avant l'appel, par modèle",
    unit="s",
    explicit_bucket_boundaries_advisory=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300],
)

# --- Queue taskiq ---


def _queue_depth_callback(options):
    """Callback appelé périodiquement par le SDK pour lire la taille de la queue.

    La queue taskiq est une liste Redis nommée "taskiq_queue" (cf. broker.py),
    sur la base Redis de dev (db 1, via redis_server_dev).
    """
    try:
        from ..redis.redis import redis_server_dev

        depth = redis_server_dev().llen("taskiq_queue")
        yield metrics.Observation(depth)
    except Exception as exc:  # défensif : ne jamais casser la collecte de métriques
        logger.debug("worker.queue.depth indisponible: %s", exc)
        yield metrics.Observation(0)


worker_queue_depth = meter.create_observable_gauge(
    "worker.queue.depth",
    callbacks=[_queue_depth_callback],
    description="Nombre de tâches en attente dans la queue taskiq",
    unit="1",
)
