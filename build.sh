#!/usr/bin/env bash
# build.sh — Script de build para Render

set -o errexit  # Detiene el script si hay cualquier error

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
