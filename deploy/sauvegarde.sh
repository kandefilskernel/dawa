#!/bin/sh
# Sauvegarde quotidienne de Dawa : base de données, photos, pièces KYC et clé RSA des jetons.
# À lancer depuis le dossier deploy/ (cron : voir DEPLOIEMENT.md). Garde les 14 dernières sauvegardes.
set -eu

cd "$(dirname "$0")"
DESTINATION="${DAWA_SAUVEGARDES:-/var/backups/dawa}"
JOUR="$(date +%Y-%m-%d_%H%M)"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"
mkdir -p "$DESTINATION"
chmod 700 "$DESTINATION"

# Base PostgreSQL (format compressé, restaurable avec pg_restore).
$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DESTINATION/base_$JOUR.dump"

# Fichiers : photos (media), pièces KYC (prive) et clé des jetons (cles).
$COMPOSE exec -T backend tar -czf - -C /app media prive cles > "$DESTINATION/fichiers_$JOUR.tar.gz"

chmod 600 "$DESTINATION"/*_"$JOUR".*
find "$DESTINATION" -type f -mtime +14 -delete
echo "Sauvegarde terminée : $DESTINATION (*_$JOUR)"
