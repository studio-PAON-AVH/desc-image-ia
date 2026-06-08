FROM python:3.10-slim
WORKDIR /app
COPY mission-apprentissage/backend/models/model1/requirements.txt .
COPY mission-apprentissage/backend/utils /app/utils
RUN pip install --no-cache-dir -r requirements.txt
COPY mission-apprentissage/backend/models/model1/saleforce_cpu_large.py .
ENV PYTHONPATH=/app
CMD ["uvicorn", "saleforce_cpu_large:app", "--host", "0.0.0.0", "--port", "8000"]