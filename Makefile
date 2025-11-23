SHELL := /bin/bash

.PHONY: help build up up-dev logs logs-db down restart sh migrate createsuperuser collectstatic shell dbshell

help:
	@echo "Targets:"
	@echo "  build           - docker compose build"
	@echo "  up              - start db+web (gunicorn)"
	@echo "  up-dev          - start db+web-dev (runserver + autoreload)"
	@echo "  logs            - follow web logs"
	@echo "  logs-db         - follow db logs"
	@echo "  down            - stop and remove containers"
	@echo "  restart         - restart web"
	@echo "  sh              - shell into web container"
	@echo "  migrate         - apply migrations"
	@echo "  createsuperuser - create superuser"
	@echo "  collectstatic   - collect static files"
	@echo "  uml             - generate UML class diagrams"

build:
	docker compose build

up:
	docker compose up -d --build

up-dev:
	docker compose --profile dev up -d --build web-dev db

logs:
	docker compose logs -f web

logs-db:
	docker compose logs -f db

down:
	docker compose down

restart:
	docker compose restart web || true

sh:
	docker compose exec web bash || docker compose exec web-dev bash

migrate:
	docker compose exec web python manage.py migrate || docker compose exec web-dev python manage.py migrate

createsuperuser:
	docker compose exec web python manage.py createsuperuser || docker compose exec web-dev python manage.py createsuperuser

collectstatic:
	docker compose exec web python manage.py collectstatic --noinput || true

uml:
	# Ensure dependencies inside container
	docker compose exec web bash -lc 'python -c "import django_extensions,pydotplus; print(\"ok\")"' || docker compose exec web pip install django-extensions pydotplus
	# Ensure system graphviz is present (for PNG/SVG rendering)
	docker compose exec web bash -lc 'command -v dot >/dev/null 2>&1 || (apt-get update && apt-get install -y graphviz)'
	# Run generator
	docker compose exec web bash -lc 'chmod +x scripts/gen_class_diagrams.sh && scripts/gen_class_diagrams.sh'
