FROM python:3.10-slim
WORKDIR /app
COPY models/model1/requirements.txt .
COPY models /app/models
RUN pip install --no-cache-dir -r requirements.txt
COPY models/model1/saleforce_cpu_large.py .
CMD ["uvicorn", "saleforce_cpu_large:app", "--host", "0.0.0.0", "--port", "8000"]