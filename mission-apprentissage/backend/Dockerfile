FROM python:3.11
WORKDIR /app
COPY mission-apprentissage/pyproject.toml .
COPY mission-apprentissage/backend /app/backend
RUN pip install --no-cache-dir -e .
ENV PYTHONPATH=/app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]