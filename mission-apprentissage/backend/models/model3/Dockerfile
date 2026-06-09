FROM python:3.11
WORKDIR /app
COPY mission-apprentissage/backend/models/model3/requirements.txt .
COPY mission-apprentissage/backend/utils /app/utils
RUN pip install --no-cache-dir -r requirements.txt
COPY mission-apprentissage/backend/models/model3/git_large.py .
ENV PYTHONPATH=/app
CMD ["uvicorn", "git_large:app", "--host", "0.0.0.0", "--port", "8000"]