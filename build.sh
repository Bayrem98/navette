#!/usr/bin/env bash
set -o errexit

echo "Python version:"
python --version

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir -p staticfiles
mkdir -p media

# Attendre que PostgreSQL soit prêt (optionnel)
echo "Waiting for database..."
sleep 5

# Run migrations
python manage.py migrate --noinput

# Collect static files - force overwrite and clear cache
echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

# List collected static files to verify
echo "Static files collected:"
ls -la staticfiles/