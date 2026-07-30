import os
from dotenv import load_dotenv
from taskiq.middlewares import SimpleRetryMiddleware
from taskiq_redis import ListQueueBroker

from .core.observability.otel_taskiq import OtelMiddleware

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")

# Queue d'orchestration : extraction epub, sauvegarde DB/MinIO, fan-out vers les
# queues modèles ci-dessous. Un seul worker suffit, ce n'est jamais lui qui
# attend les appels aux modèles IA.
#
# SimpleRetryMiddleware est ce qui fait effectivement fonctionner les labels
# retry_on_error/max_retries posés sur les tâches (@broker.task(...)) : sans
# cette middleware ces labels sont lus par personne et le retry ne se déclenche
# jamais.
broker = ListQueueBroker(REDIS_URL, socket_timeout=None, queue_name="taskiq_queue").with_middlewares(
    OtelMiddleware(), SimpleRetryMiddleware()
)

# Une queue Redis dédiée par modèle IA : chacune est consommée par son propre
# worker (cf. docker-compose), ce qui permet de scaler/redémarrer un modèle
# indépendamment des autres au lieu de tout concentrer dans un seul worker qui
# appelle les 3 modèles en interne via httpx.
broker_salesforce = ListQueueBroker(
    REDIS_URL, socket_timeout=None, queue_name="queue_salesforce_blip"
).with_middlewares(OtelMiddleware(), SimpleRetryMiddleware())

broker_florence2 = ListQueueBroker(
    REDIS_URL, socket_timeout=None, queue_name="queue_florence2"
).with_middlewares(OtelMiddleware(), SimpleRetryMiddleware())

broker_git = ListQueueBroker(
    REDIS_URL, socket_timeout=None, queue_name="queue_git_large"
).with_middlewares(OtelMiddleware(), SimpleRetryMiddleware())

# Clé interne du modèle (cf. epub/service.MODEL_KEYS) -> broker de sa queue.
MODEL_BROKERS = {
    "salesforce_blip": broker_salesforce,
    "florence2": broker_florence2,
    "git_large": broker_git,
}
