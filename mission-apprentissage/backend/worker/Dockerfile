FROM python:3.12.13-slim-bookworm
WORKDIR /app
COPY mission-apprentissage/pyproject.toml .
COPY mission-apprentissage/backend /app/backend
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -e .
ENV PYTHONPATH=/app
CMD ["python", "-m", "taskiq", "worker", "backend.worker.worker:broker", "--workers", "1"]