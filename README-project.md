# Lumiere Secrète

Веб-приложение для управления каталогом и заказами fashion-бутика.

## Архитектура

- **Backend** — Django 4.2 + Django REST Framework. Приложения:
  - `accounts` — пользователи, роли (администратор, менеджер, клиент), настройки профиля.
  - `catalog`/`product_variants` — товары, варианты, изображения, отзывы и избранное.
  - `orders` — заказы, истории статусов, платежи, CRUD/API.
  - `reports` — аналитика, SQL-представления и графики.
  - `admin_tools` — резервное копирование и восстановление.
- **База данных** — PostgreSQL (см. `DATABASES` в `lumieresecrete/settings/base.py`), миграции создают внешние ключи, ограничения и SQL-представления.
- **RBAC** — гости (аноним), клиенты, менеджеры и администраторы. Навигация и API учитывают роль через `is_manager`/`is_staff`.
- **Фронтенд** — Django templates + адаптивные стили (`catalog/static/catalog/catalog.css`) с несколькими брейкпоинтами; горячие клавиши подключены через `static/catalog/hotkeys.js`.

## Роли

| Роль         | Возможности                                                                 |
|--------------|------------------------------------------------------------------------------|
| Гость        | Просмотр каталога, регистрация/вход.                                        |
| Клиент       | Покупки, избранное, история заказов, пользовательские настройки.           |
| Менеджер     | Панель менеджера, аналитика, модерация отзывов, экспорт отчётов.            |
| Администратор| Полный доступ, включая Django Admin и резервные копии.                      |

## Запуск (локально)

1. Требования: Python 3.9+, PostgreSQL, `libffi`/`cairo` для WeasyPrint.
2. Склонируйте репозиторий и создайте `.env` с параметрами базы, например:
   ```
   DJANGO_SECRET_KEY=dev-secret
   DJANGO_DEBUG=True
   DJANGO_DB_ENGINE=django.db.backends.postgresql
   DJANGO_DB_NAME=lumieresecrete
   DJANGO_DB_USER=postgres
   DJANGO_DB_PASSWORD=password
   DJANGO_DB_HOST=localhost
   DJANGO_DB_PORT=5432
   DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   DJANGO_EMAIL_HOST=smtp.your-provider.com
   DJANGO_EMAIL_PORT=587
   DJANGO_EMAIL_USE_TLS=True
   DJANGO_EMAIL_HOST_USER=sinitsyna-liza@inbox.ru
   DJANGO_EMAIL_HOST_PASSWORD=VN68cP1NQK1MprnBAUid
   DJANGO_DEFAULT_FROM_EMAIL="Lumiere Secrète <sinitsyna-liza@inbox.ru>"
   ```
3. Установите зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Примените миграции и создайте суперпользователя:
   ```bash
   cd lumieresecrete
   python manage.py migrate
   python manage.py createsuperuser
   ```
5. Запустите сервер:
   ```bash
   python manage.py runserver
   ```

## Запуск в контейнере

1. Скопируйте `.env` в корень (значения те же, что и для локального запуска).
2. Соберите образ:
   ```bash
   docker build -t lumieresecrete .
   ```
3. Выполните миграции и поднимите сервер (пример с docker run):
   ```bash
   docker run --env-file .env -p 8000:8000 lumieresecrete
   ```
Образ запускает миграции при старте и поднимает `gunicorn` на `0.0.0.0:8000`.

## Запуск через docker-compose

Рекомендуемый способ для локальной разработки и демо.

1) Подготовьте файл окружения
   - Создайте файл `.env` в корне: можно взять за основу `.env.example` и при необходимости изменить значения.
   - Для запуска в compose параметр `DJANGO_DB_HOST` должен быть `db` (в `.env.example` уже так).

2) Соберите и поднимите сервисы
   ```bash
   docker compose up -d --build
   ```

3) Проверьте логи приложения
   ```bash
   docker compose logs -f web
   ```

4) (Опционально) Загрузите демо-данные
   - Укажите путь к файлу фикстуры в переменной `INITIAL_FIXTURE`, например:
     `INITIAL_FIXTURE=/srv/app/lumieresecrete/backups/backup-20251114-214816.json`
   - Можно добавить это прямо в `docker-compose.yml` (см. комментарий внутри) или во время запуска:
     ```bash
     INITIAL_FIXTURE=/srv/app/lumieresecrete/backups/backup-20251114-214816.json \
       docker compose up -d --build
     ```

5) Создайте суперпользователя
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

6) Откройте приложение
   - Браузер: http://localhost:8000/
   - Админка: http://localhost:8000/admin/

Полезные команды:
- Остановить сервисы: `docker compose down`
- Пересобрать после изменений: `docker compose up -d --build`
- Перезапустить только веб: `docker compose restart web`
- Подключиться в shell контейнера: `docker compose exec web bash`

### Режим разработки (автоперезагрузка)

- Запуск dev-профиля (авторелоад, монтирование кода):
  ```bash
  docker compose --profile dev up -d --build web-dev db
  ```
- Логи dev:
  ```bash
  docker compose logs -f web-dev
  ```
- В dev-контейнере код из `./lumieresecrete` смонтирован внутрь, изменения подтягиваются без пересборки.

### Makefile (короткие команды)

- `make up` — поднять prod-профиль (gunicorn)
- `make up-dev` — поднять dev-профиль (runserver + autoreload)
- `make logs` / `make logs-db` — логи
- `make migrate` / `make createsuperuser` — служебные действия
- `make sh` — зайти в контейнер

### pgAdmin (графический веб-интерфейс для PostgreSQL)

- Доступ: http://localhost:5050
- Учётные данные: переменные `PGADMIN_DEFAULT_EMAIL` и `PGADMIN_DEFAULT_PASSWORD` из `.env` (см. `.env.example`).
- Подключение к базе:
  - Host: `db`
  - Port: `5432`
  - Username/Password: из переменных `DJANGO_DB_USER` / `DJANGO_DB_PASSWORD`
  - Database: `DJANGO_DB_NAME`

### Healthchecks

- `db` — проверяется `pg_isready` до готовности.
- `web`/`web-dev` — проверяется доступность порта 8000 из контейнера.

## OpenAPI

Документация REST API описана в `docs/api/openapi.yaml` (формат OpenAPI 3.0). Файл включает операции:

- `GET /orders/api/orders/` — список заказов;
- `POST /orders/api/orders/` — создание;
- `GET /orders/api/orders/{id}/` — детали;
- `POST /orders/api/orders/{id}/update/` — обновление;
- `POST /orders/api/orders/{id}/delete/` — удаление.

Чтобы визуализировать спецификацию, импортируйте файл в Swagger UI, Postman или любой OpenAPI-совместимый инструмент.
