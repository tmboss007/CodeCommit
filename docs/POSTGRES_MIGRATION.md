# PostgreSQL + PostGIS migration

Status after this phase is recorded in `docs/PROGRESS.md`. This file is the audit and the design that was implemented. SQLite remains a supported unit-test / local fallback. Do not delete `backend/nexus_r.db`; copy it before switching a machine to Postgres.

## Backup / rollback

Known-good SQLite file (working demo):

```text
backend/nexus_r.db
```

Copy before changing `DATABASE_URL`:

```text
mkdir backend\backups
copy backend\nexus_r.db backend\backups\nexus_r.sqlite.bak
```

Rollback: set `DATABASE_URL=sqlite:///./nexus_r.db`, restart the API. Simulation RESET/LOAD still recreates schema via SQLAlchemy `create_all`.

If Postgres breaks the closed-loop demo: keep SQLite, do not force Postgres as the only path.

## Audit (pre-change)

### 1. SQLite-specific logic

| Location | Behavior |
| --- | --- |
| `app/core/database.py` | `check_same_thread` when URL starts with `sqlite`. `ensure_schema()` ran `create_all` then SQLite-only `ALTER TABLE` for `app_state.last_plan_*`, `active_plan_id`, `coordination_tasks.plan_id`. Non-SQLite returned immediately (no PostGIS). |
| `app/core/database_sqlite.py` | Unused parallel engine hardcoded to `sqlite:///./nexus_r.db`. Left in place. |
| `app/main.py` | On missing columns, `drop_all` + `create_all` (safe-ish on empty SQLite; dangerous on Postgres with data). Postgres path now refuses this drop. |
| `docker-compose.yml` | Previously `DATABASE_URL: sqlite:///./nexus_r.db`. |
| `backend/.env.example` | Default SQLite. |
| Tests | `Base.metadata.drop_all/create_all` against whatever `DATABASE_URL` is (typically SQLite). |
| `scripts/seed_sqlite.py` | SQLite seed without geometry. |

No other raw SQL dialect branches were found (`?` placeholders, `AUTOINCREMENT`, etc.).

### 2. Spatial data

ORM stores **float `latitude` / `longitude`** on `Zone`, `Resource`. Incidents have no lat/lon; they inherit a zone.

Distance/ETA is Python `geopy.geodesic` (`priority.calculate_distance_km`) used by routing simulation, optimizer inputs, and nearest-zone for GDACS ingest.

`scripts/seed_demo_data.py` previously assigned GeoAlchemy `WKTElement` `location=` on models that **do not have** a `location` column — that script would fail. Canonical demo seed is `app/services/demo_seed.py` (5 zones, 5 agencies, **15** resources).

Alembic `001_initial_migration.py` is Postgres/PostGIS-oriented and **stale vs live models**: required `zones.location` POINT, optional incident/resource `location`, missing `plans`, `app_state`, `priority_breakdown`, `duplicate_status`, allocation `from_zone_id` / `approved_by`, `coordination_tasks.plan_id`.

### 3. UUID handling

Primary keys are **strings** (`ZONE_A`, `plan_…`, `R01`). Not PostgreSQL `UUID`. Unchanged.

### 4. Datetime

Naive `datetime.utcnow` → `DateTime` columns. Maps to `timestamp without time zone`. Unchanged.

### 5. JSON

SQLAlchemy `JSON` on breakdowns, capabilities, audit payloads, app_state snapshots. PostgreSQL `JSON` (not forced JSONB). Unchanged.

### 6. Enum / status

Statuses are **strings** (`available`, `pending_approval`, `NEW`, …), not PG ENUM types. Unchanged.

### 7. Transactions

`SessionLocal(autocommit=False)`. SSE still publishes after commit. Unchanged.

### 8. Dev initialization

`ensure_schema()` + simulation RESET `drop_all`/`create_all`. Alembic `env.py` ignored `DATABASE_URL` and used `alembic.ini` (`postgresql://postgres:password@localhost:5432/nexus_r`). Driver in requirements: **psycopg2** (`postgresql+psycopg2://`). `postgresql+psycopg://` would need psycopg3 — not added.

### 9. Redis

`REDIS_URL` exists in settings; **no runtime Redis client**. Compose does not start Redis.

## Target design (implemented)

- Production/demo: PostgreSQL 14+ with PostGIS. Preferred start: `docker compose up --build`.
- Unit tests: SQLite unless `DATABASE_URL` is Postgres.
- API schemas still expose lat/lon. Frontend unchanged.
- ORM does **not** declare Geometry columns (SpatiaLite is not required for SQLite tests).
- On Postgres, `ensure_schema` / Alembic `002` add nullable `geometry(Point,4326)` `location` on `zones`, `resources`, `incidents`, GIST indexes, operational indexes, and backfill from lat/lon (incidents copy the zone point).
- Nearest-zone for ingest uses `ST_Distance` / `<->` on Postgres and the existing geodesic on SQLite. **One helper**, two dialects — optimizer still receives Python distances.
- `001` left as historical; `002` adds the live schema extras and makes `zones.location` nullable so ORM inserts work.

## Environment

| Variable | Example |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://codecommit:codecommit@localhost:5432/nexus_r` |
| Compose host | `postgres` (service name), port `5432` |
| Database | `nexus_r` |
| User / password | `codecommit` / `codecommit` (local demo only; not for production) |

Do not put credentials in the frontend. Do not commit `.env`.

## Spatial queries moved to PostGIS

- Nearest zone for external ingest (`ingest_external_event`).

Not moved (by design): OR-Tools distance matrix, routing simulation ETAs.

## Verification (this environment)

- pytest (SQLite `DATABASE_URL`): 57 passed, 4 skipped (PostGIS)
- `npx tsc --noEmit` / `npm run build`: succeeded
- `/health` on local API: `database=sqlite`, `postgis=false`
- Closed loop against SQLite API: RESET → LOAD (5/5/15) → approve → inject → replan → Zone A 60.76→82.47 → approve revised (`active` switched to new plan). Audit 82 events. GDACS `SIMULATION`
- Docker CLI was **not installed** (`docker` not on PATH). PostGIS pytest and Postgres browser demo were **not** run. Status: **PARTIALLY IMPLEMENTED**

## Verification gate

Do not promote this status until all of the following are complete against PostgreSQL:

1. `docker compose up --build` starts Postgres, API, and frontend.
2. `alembic upgrade head` succeeds on a fresh database using `postgresql+psycopg2://...`.
3. `SELECT PostGIS_Full_Version();` succeeds; zones, resources, and incidents have spatial points and the expected GIST index exists.
4. Nearest-zone ingest uses the PostGIS path.
5. The browser workflow completes without database edits: RESET, LOAD, approve, urgent report, revised-plan review and approval, resources, coordination, agents, audit, refresh, and persistence.

Until that gate passes, SQLite remains the proven fallback and PostgreSQL/PostGIS stays **PARTIALLY IMPLEMENTED**. Simulation RESET is a development operation that drops and recreates schema; it must not be used against a production-like Postgres database.

