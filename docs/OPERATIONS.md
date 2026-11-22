# Analyst pilot operations

## Prepare and run

Use a project-local Python 3.11 environment. From this repository:

```powershell
python -m pip install -r requirements-dev.txt
python data/create_db.py
python -m pytest -q
python scripts/run_benchmark.py
python -m uvicorn api.app:app --host 127.0.0.1 --port 8040 --workers 1
```

The generated SQLite database is a seeded synthetic fixture and is ignored by Git.
`POST /api/metrics` accepts allowlisted metrics and filters; `/api/schema` describes
the available data. No caller-provided SQL or Python is executed. A deterministic
tool-regression pass does not establish natural-language answer quality.

Start the UI in another terminal with the same environment:

```powershell
$env:ANALYST_API_URL = 'http://127.0.0.1:8040'
python -m streamlit run streamlit_app/app.py --server.address 127.0.0.1 --server.port 8540
```

## Model and authentication

Set `ANALYST_MODEL` to an exact provider-supported model ID. For Ollama, run the
model separately and set `OLLAMA_BASE_URL`. For hosted Gemini, configure
`GOOGLE_API_KEY` server-side outside Git and verify account/credit applicability
before a controlled call. No hosted model is selected or billed by these instructions.
Neither the API nor the UI loads a local `.env` automatically; Docker Compose reads
the ignored `.env`, while native execution needs environment variables.

For a private remote pilot set `APP_ENV=production` and a random `ANALYST_API_KEY`
of at least 32 characters. Authorized clients send `X-API-Key`; the Streamlit server
needs the same key in its environment. Keep ports on loopback behind TLS and an
authenticated access proxy. The key identifies an operator, not individual tenants.
Provider credentials are excluded from the read-only MCP subprocess environment.

`/live` checks the process. `/ready` checks model configuration and readable data;
it deliberately does not make a paid provider call. `/health` is a descriptive
status endpoint, not a provider-connectivity test. An unconfigured model yields
503 on `/api/analyze`, while deterministic metrics remain usable.

## Limits and failure handling

Requests are capped at 64 KiB. One process permits two analyses, with eight model
calls, 128 events, bounded answer output and a 60-second deadline per run. Overload
returns 429 with `Retry-After`; timeout returns 504; provider/output failures return
502. Cancellation is best effort and does not guarantee provider billing stops.
Gateways need per-user quotas before broader use; adding workers multiplies limits.

Keep API keys and raw prompts out of logs and screenshots. Responses include model,
elapsed time and available token usage; no invented monetary-cost estimate is used.
Live answer quality, provider failure behavior and actual token spend still require
a separately frozen and labeled evaluation.

## Containers and rollback

Copy `.env.example` to ignored `.env` and configure only the needed provider. Run
`docker compose up --build -d`; API/UI bind to loopback 8040/8540. The image runs
as a non-root user and includes a generated synthetic fixture. Stop using
`docker compose down`. Preserve a known-good image ID and model/prompt/tool versions;
roll back the complete set, check `/ready`, then run the independent aggregate checks
and a small controlled model evaluation. The database contains no user conversations;
ADK session state is in memory and is not durable across restart.
