"""Clés Redis et helpers partagés entre le worker (process_epub_describe et les
tâches par modèle dans backend/worker/) et l'API (endpoint d'annulation dans
backend/tasks/) pour coordonner le fan-out d'une tâche EPUB à travers
plusieurs queues taskiq.

Prend le client Redis en paramètre (plutôt que d'en garder un ici) pour que
chaque module conserve le sien, mockable indépendamment dans les tests.
"""

MODEL_KEYS = ("salesforce_blip", "florence2", "git_large")
NUM_MODELS = len(MODEL_KEYS)

# Durée de vie des clés de coordination : garde-fou pour ne jamais accumuler
# de clés orphelines si une tâche ne se termine jamais proprement (crash...).
COORDINATION_TTL_SECONDS = 24 * 3600


def cancel_key(task_id: str) -> str:
    return f"cancel:{task_id}"


def remaining_key(task_id: str) -> str:
    """Nombre de sous-tâches (batch, modèle) restant à traiter pour la tâche."""
    return f"remaining:{task_id}"


def processed_key(task_id: str) -> str:
    """Nombre d'images pour lesquelles les 3 modèles ont fini (succès ou non)."""
    return f"processed:{task_id}"


def image_done_key(task_id: str, image_id: int) -> str:
    """Nombre de modèles ayant traité une image donnée (0..NUM_MODELS)."""
    return f"imgdone:{task_id}:{image_id}"


def started_key(task_id: str) -> str:
    """Horodatage (time.monotonic) du début de traitement, pour task.duration."""
    return f"started:{task_id}"


def is_cancelled(r, task_id: str) -> bool:
    return bool(r.exists(cancel_key(task_id)))


def mark_cancelled(r, task_id: str) -> None:
    r.set(cancel_key(task_id), "1", ex=COORDINATION_TTL_SECONDS)
