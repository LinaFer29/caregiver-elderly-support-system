#!/bin/sh
set -eu

mkdir -p /app/media/assistant_audio /app/staticfiles /app/.cache/huggingface

if [ -z "$(find /app/staticfiles -mindepth 1 -maxdepth 1 2>/dev/null)" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
