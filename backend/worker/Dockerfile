FROM python:3.12.13-slim-bookworm
WORKDIR /app

ENV POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN python -m pip install --upgrade pip && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY ./backend/pyproject.toml ./backend/poetry.lock ./
RUN poetry install --only main --no-cache

COPY ./backend /app/backend
ENV PYTHONPATH=/app

# Cible taskiq (module:broker) à consommer par ce container. Par défaut,
# l'orchestrateur (extraction + fan-out) ; surchargé par docker-compose pour
# les workers dédiés à chaque modèle (backend.worker.model_tasks:broker_xxx).
ENV TASKIQ_BROKER=backend.worker.worker:broker
CMD python -m taskiq worker ${TASKIQ_BROKER} --workers 1
