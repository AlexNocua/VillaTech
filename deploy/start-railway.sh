#!/bin/sh
set -eu
cd /app/backend
mkdir -p "${MEDIA_ROOT:-/data/media}"
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 60 --access-logfile - --error-logfile -
