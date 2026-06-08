FROM python:3.10-slim
WORKDIR /app
COPY models/model1/requirements.txt .
COPY models /app/models
RUN pip install --no-cache-dir -r requirements.txt
COPY models/model1/blip2opt.py .
CMD ["uvicorn", "blip2opt:app", "--host", "0.0.0.0", "--port", "8000"]