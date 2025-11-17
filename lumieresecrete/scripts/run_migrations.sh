#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")/.."

# Activate the virtual environment
source ../venv/bin/activate

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Exit the script
exit 0