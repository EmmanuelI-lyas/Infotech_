# Dashboard Docker Setup (PostgreSQL + Superset)

This folder contains a complete Docker setup for:
- PostgreSQL (stores Titanic data and Superset metadata DB)
- Superset (dashboard UI)
- Optional seed container to load `../titanic/train.csv` into PostgreSQL
- Optional import hook for your existing exported Superset dashboard/assets

## 1) Keep your existing secrets (optional env file)

You can keep your current secrets exactly as they are.

- If `superset/superset_config.py` already has your `SECRET_KEY`, no change is required.
- A `.env` file is optional and only needed if you want to override defaults (DB user/password/ports/admin user).

If you want to use `.env`, create it manually in this folder and add only the values you want to override.

## 2) Start PostgreSQL + Superset

```bash
docker compose up -d --build
```

By default in this setup:
- Superset metadata DB is `titanic_db`
- A DB connection named `Titanic PostgreSQL` is auto-created in Superset

Superset will be available at:
- http://localhost:8088

If you do not set env vars, defaults are used (`admin` / `admin`).

## 3) (Optional) Load Titanic data into PostgreSQL

Run the seed profile once:

```bash
docker compose --profile seed up --build postgres-seed
```

This loads `../titanic/train.csv` into `${POSTGRES_DB}.${TITANIC_TABLE}`.

## 4) Connect Superset to Titanic DB

This is now automatic by default via `superset-init`.

If you still want to add it manually in UI:

Inside Superset UI:
1. Settings -> Database Connections -> + Database
2. SQLAlchemy URI:

```text
postgresql+psycopg2://<POSTGRES_USER>:<POSTGRES_PASSWORD>@postgres:5432/<POSTGRES_DB>
```

If entering from your host machine tools, use `localhost` instead of `postgres`.

## 5) Deploy your existing Superset dashboard

If you already have exported Superset assets, place them here:

- `19_jun/dashboard/superset/imports/dashboards.zip`
- `19_jun/dashboard/superset/imports/datasets.zip` (optional)

Then recreate init + app:

```bash
docker compose up -d --build --force-recreate superset-init superset
```

`superset-init` will import those files automatically if they exist.

## Useful commands

Stop services:

```bash
docker compose down
```

Stop and remove volumes (deletes DB data):

```bash
docker compose down -v
```
