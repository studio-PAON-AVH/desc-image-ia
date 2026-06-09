FROM python:3.12.13-slim-bookworm
WORKDIR /app
COPY mission-apprentissage/backend/models/model3/requirements.txt .
COPY mission-apprentissage/backend/utils /app/utils
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY mission-apprentissage/backend/models/model3/git_large.py .
ENV PYTHONPATH=/app
CMD ["uvicorn", "git_large:app", "--host", "0.0.0.0", "--port", "8000"]