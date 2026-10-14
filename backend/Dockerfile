FROM python:3.12-slim

# Bibliothèques géographiques requises par GeoDjango
RUN apt-get update \
    && apt-get install -y --no-install-recommends binutils libproj-dev gdal-bin fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Production : gunicorn. En développement, docker-compose remplace cette commande par runserver.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "30"]
