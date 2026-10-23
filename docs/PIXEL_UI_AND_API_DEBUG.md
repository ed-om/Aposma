# Aposma pixel UI and API diagnostics

## Apply the patch

Extract the supplied patch ZIP into the repository root (`~/Downloads/aposma`) and allow it to overwrite the listed files. It intentionally does not replace `frontend/package.json` or `package-lock.json`, so existing dependency work is preserved.

## Start the API

From the repository root, activate the project's virtual environment if it has one, then run:

```bash
cd ~/Downloads/aposma
source .venv/bin/activate
export APOSMA_ANALYZER_BIN="$HOME/Downloads/aposma-analyzer-fix/build/aposma-analyzer"
python -m uvicorn codelens.server:app --host 127.0.0.1 --port 8000 --reload
```

If the analyzer binary is at a different path, update `APOSMA_ANALYZER_BIN`. Confirm the API response in another terminal:

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/api/status
```

`/health` should return HTTP 200 and `{"status":"ok"}`. `/api/status` should return HTTP 200 with analyzer and Ollama status. Analyzer or Ollama not being ready is reported in the JSON; it should not make the whole status endpoint fail.

## Start the frontend

Use a separate terminal:

```bash
cd ~/Downloads/aposma/frontend
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite dev server proxies `/api` requests to `127.0.0.1:8000`.

## Diagnose an HTTP 500

The browser now shows the HTTP status and a short diagnostic message. The FastAPI terminal logs the full traceback for an unexpected server exception. If `/api/review` still returns HTTP 500, copy the traceback from the terminal running Uvicorn; the browser network panel alone does not include the failing Python line.
