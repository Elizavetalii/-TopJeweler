FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/app

# System deps for WeasyPrint (PDF), and runtime basics
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libcairo2 \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf-2.0-0 \
       libffi-dev \
       fonts-dejavu-core \
       graphviz \
       shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /srv/app/lumieresecrete

# Ensure entrypoint is executable
RUN chmod +x /srv/app/docker/entrypoint.sh || true

EXPOSE 8000

ENTRYPOINT ["/srv/app/docker/entrypoint.sh"]
CMD ["gunicorn", "lumieresecrete.wsgi:application", "--bind", "0.0.0.0:8000"]
