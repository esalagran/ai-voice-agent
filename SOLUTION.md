# Prosper Challenge Solution

## Task 1: EHR HTTP API

This solution adds a small EHR HTTP service for the first deliverable:

- create a patient
- find a patient by name and date of birth
- list available appointment slots
- create an appointment
- cancel an appointment

The service is separate from the voice bot and runs as its own FastAPI app from `ehr.py`.

## API

The endpoints keep the challenge operation names:

- `POST /rpc/create_patient`
- `GET /rpc/find_patient`
- `GET /rpc/list_availability_slots`
- `POST /rpc/create_appointment`
- `PUT /rpc/cancel_appointment`

FastAPI provides the OpenAPI docs at:

```text
http://127.0.0.1:7861/docs
```

## Persistence

The EHR uses SQLAlchemy with SQLite by default:

```text
sqlite:///./ehr.db
```

The database URL can be changed with:

```bash
EHR_DATABASE_URL=sqlite:///./ehr.db
```

SQLite is enough for this first task because it is file-backed, simple to run locally, and survives process restarts. A production version would move this to Postgres and add migrations.

## Running

Seed deterministic demo data:

```bash
uv run python ehr.py --seed
```

Start the EHR service:

```bash
uv run python ehr.py
```

It starts on `127.0.0.1:7861` by default.

## Tests And CI

The EHR tests live under `ehr_service/tests/`. They cover the HTTP flow, persistence, domain date
validation, name normalization, and patient deduplication.

Run locally:

```bash
uv run ruff check .
uv run pyright
uv run python -m pytest
```

The GitHub Actions workflow in `.github/workflows/ci.yml` runs the same lint, typecheck, and test
commands on pull requests and pushes to `main`.

## Tradeoffs

- No authentication yet; this is local challenge infrastructure.
- No Alembic migrations yet; `create_all` is enough for the first task schema.
- No appointment search endpoint yet; cancellation currently uses the appointment ID.
