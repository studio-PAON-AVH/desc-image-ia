FROM python:3.12.13-slim-bookworm
WORKDIR /app
COPY mission-apprentissage/pyproject.toml .
COPY mission-apprentissage/django_app /app/frontend
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -e .
ENV PYTHONPATH=/app/frontend
CMD ["python", "frontend/manage.py", "runserver", "0.0.0.0:7001"]