FROM python:3.11-slim
WORKDIR /app
COPY mission-apprentissage/pyproject.toml .
COPY mission-apprentissage/backend /app/backend
RUN pip install --no-cache-dir -e .
ENV PYTHONPATH=/app
CMD ["python", "-m", "taskiq", "worker", "backend.worker.worker:broker"]