# VitalStep Sync API

Minimal FastAPI service to sync Supabase patient readings into HubSpot contacts.

Quick start

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill values.

3. Run locally:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints

- `GET /health` — health check
- `POST /sync/supabase` — start a background sync job
- `POST /sync/supabase/block` — run sync synchronously and return result

Deploying to Render

- Create a new Web Service on Render.
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add environment variables in Render for `HUBSPOT_PAT`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY`.
