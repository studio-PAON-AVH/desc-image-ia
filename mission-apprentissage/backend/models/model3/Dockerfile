FROM python:3.10-slim
WORKDIR /app
COPY models/model3/requirements.txt .
COPY utils /app/utils
RUN pip install --no-cache-dir -r requirements.txt
COPY models/model3/git_large.py .
ENV PYTHONPATH=/app
CMD ["uvicorn", "git_large:app", "--host", "0.0.0.0", "--port", "8000"]