# Repository Guidelines

## Project Structure & Modules
- `ksys_app/`: Reflex app (pages, states, components, queries, ai_engine, utils, config). Entry: `ksys_app/ksys_app.py`.
- `dagster/`: Orchestration (Compose files, user-code/webserver Dockerfiles).
- Tests: `ksys_app/tests/` and root `test_*.py` (DB, pandas, integration).
- `assets/`, `docs/` (e.g., `docs/GIT_WORKFLOW_GUIDE.md`). Root: `rxconfig.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`.

Deprecated
- `node-red/`: Legacy flows; do not modify. Orchestration is migrating to Dagster.

## Build, Test, and Dev Commands
- Install: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt` (Windows: `venv\Scripts\activate`).
- App (local): `reflex run` (FE `:13000`, BE `:13001`). Docker: `docker compose up --build`.
- Dagster: `docker compose -f dagster/dagster-compose.yml up -d` (web UI on `:3001`).
- Tests: `pytest -q ksys_app/tests test_*.py` (e.g., `-k security`).

## Coding Style & Naming
- Python: PEP8, 4-space indent, type hints for `rx.State` fields and public APIs.
- Names: files/modules `snake_case.py`; classes `PascalCase`; functions/vars `snake_case`.
- Reflex: business logic in `State`; UI returns `rx.Component`. Pages under `ksys_app/pages`, reusable UI under `ksys_app/components`.
- Pipelines: keep Dagster jobs/ops small and typed; config via env.
- SQL/DB: parameter binding only; time bounds/limits required (see `CODING_RULES.md`).

## Testing Guidelines
- Framework: `pytest`; tests live in `ksys_app/tests/` and root `test_*.py`.
- Focus: state reducers, KPI calculations, security, DB adapters. Mock external I/O.
- Examples: `pytest -q ksys_app/tests/test_security.py`, `pytest -q -k pandas`.

## Commit & Pull Requests
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`) as in current history.
- PRs: clear “what/why”, linked issues, migration notes. For UI, add screenshots/GIFs; update `ksys_app/PRD.md` and tests when behavior changes.

## Security & Configuration
- Env: create `.env` from `.env.example`; set `TS_DSN`, `POSTGRES_CONNECTION_STRING`, `APP_ENV`. Never commit secrets.
- App config in `rxconfig.py`; Docker ports map `13000/13001`. Dagster’s compose spins a local Postgres for orchestration metadata (replace with managed DB for prod).

## Architecture Overview
- UI/API: Reflex (single codebase) per `rxconfig.py` ports.
- Orchestration: Dagster jobs/ops for data pipelines and scheduled tasks.
- Integration: Shared Postgres/Timescale via `TS_DSN`/`POSTGRES_CONNECTION_STRING`.
- Legacy: Node‑RED is deprecated; replace flows with Dagster assets/jobs.
