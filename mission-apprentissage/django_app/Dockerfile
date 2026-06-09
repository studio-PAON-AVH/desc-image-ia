FROM python:3.11
WORKDIR /app
COPY mission-apprentissage/pyproject.toml .
COPY mission-apprentissage/django_app /app/frontend
RUN pip install --no-cache-dir -e .
ENV PYTHONPATH=/app/frontend
CMD ["python", "frontend/manage.py", "runserver", "0.0.0.0:7001"]