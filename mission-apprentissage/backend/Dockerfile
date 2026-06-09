FROM python:3.12.13-slim-bookworm
WORKDIR /app
COPY mission-apprentissage/pyproject.toml .
COPY mission-apprentissage/backend /app/backend
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -e .
ENV PYTHONPATH=/app
CMD ["sh", "-c", "alembic -c /app/backend/alembic.ini upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]