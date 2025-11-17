FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /srv/app/lumieresecrete

CMD ["bash", "-c", "python manage.py migrate && gunicorn lumieresecrete.wsgi:application --bind 0.0.0.0:8000"]
