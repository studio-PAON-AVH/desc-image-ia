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
CMD ["python", "-m", "taskiq", "worker", "backend.worker.worker:broker", "--workers", "1"]
