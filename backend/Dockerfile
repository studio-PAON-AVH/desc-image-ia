FROM node:23-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM python:3.12.13-slim-bookworm
WORKDIR /app

ENV POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN python -m pip install --upgrade pip && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY ./backend/pyproject.toml ./backend/poetry.lock ./
RUN poetry install --only main --no-cache

COPY ./backend /app/backend
COPY --from=frontend-build /frontend/dist /app/frontend_dist

ENV PYTHONPATH=/app
CMD ["sh", "-c", "alembic -c /app/backend/alembic.ini upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]



