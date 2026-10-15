#!/bin/sh
# Démarrage du backend en production : migrations, fichiers statiques, clé RSA si absente, puis gunicorn.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Première installation : crée la clé qui signe les jetons d'appareil (conservée dans le volume « cles »).
if [ -z "$JWT_CLE_PRIVEE" ] && [ ! -f /app/cles/jwt_prive.pem ]; then
    python manage.py generer_cle_rsa
fi

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 60 \
    --forwarded-allow-ips "*" \
    --access-logfile -
