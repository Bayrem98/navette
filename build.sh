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

# Afficher les variables d'environnement pour debug
echo "DATABASE_URL: $DATABASE_URL"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"

# Attendre que PostgreSQL soit prêt
echo "Waiting for database..."
sleep 10

# Run migrations avec le bon settings
echo "Running migrations..."
python manage.py migrate --noinput --settings=transport_app.settings

python creer_superuser.py

# Collect static files avec le bon settings
echo "Collecting static files..."
python manage.py collectstatic --no-input --clear --settings=transport_app.settings

# List collected static files to verify
echo "Static files collected:"
ls -la staticfiles/ || echo "No static files found"