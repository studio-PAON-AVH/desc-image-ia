FROM python:3.11
WORKDIR /app
COPY mission-apprentissage/backend/models/model2/requirements.txt .
COPY mission-apprentissage/backend/utils /app/utils
RUN pip install --no-cache-dir -r requirements.txt
COPY mission-apprentissage/backend/models/model2/florence2_large.py .
ENV PYTHONPATH=/app
CMD ["uvicorn", "florence2_large:app", "--host", "0.0.0.0", "--port", "8000"]