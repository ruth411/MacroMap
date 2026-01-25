# Financial Analyst Copilot (SEC EDGAR RAG)

A full-stack prototype that turns SEC EDGAR filings (10-K/10-Q) into a searchable, citeable knowledge base and lets you ask questions through a chat UI. The backend ingests filings, parses them into sections, chunks + embeds the text, stores vectors in ChromaDB, and answers questions using Retrieval-Augmented Generation (RAG). The frontend is a lightweight Next.js chat experience.

---

## What’s in this repo (source of truth)

### Backend (FastAPI)
- EDGAR ingestion (download + parse filings into sections)
- Chunking with overlap + metadata (ticker, form, accession, section, etc.)
- Vector store: **ChromaDB (persistent)**
- Embeddings: **OpenAI `text-embedding-3-small`**
- LLM providers supported (generation): OpenAI / Ollama / Bedrock / HuggingFace (via an adapter)
- RAG chat endpoint with inline **Sources** appended when retrieval is used
- Deployment entrypoints for **Railway** and **Vercel** (serverless handler)

### Frontend (Next.js)
- Landing page + `/chat` page
- Calls backend for health + chat
- Minimal UI components (chat, status pill, clear session)

---

## Quickstart (local)

### 1) Prerequisites
- Node.js 18+ (or 20+ recommended)
- Python 3.10+
- An EDGAR-compliant **User-Agent** (required by SEC)
- OpenAI API key (required for embeddings; generation can use other providers but embeddings are OpenAI-only in this repo)

### 2) Clone
```bash
git clone https://github.com/ruth411/MacroMap.git
cd MacroMap-main
```

> If your folder name differs (e.g., `MacroMap`), adjust the paths accordingly.

---

## Backend setup (FastAPI)

### 1) Create venv + install deps
```bash
cd backend

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Configure environment variables
Create `backend/.env` (or export variables in your shell):

```bash
# Required for EDGAR requests (SEC policy)
SEC_USER_AGENT="Your Name your.email@domain.com"

# Required for embeddings (OpenAI)
OPENAI_API_KEY="sk-..."

# Optional: choose your generation provider (defaults vary by config)
# Examples:
LLM_PROVIDER="openai"        # openai | ollama | bedrock | huggingface
OPENAI_MODEL="gpt-4o-mini"   # or your preferred model
```

### 3) Run the backend
```bash
uvicorn app.main:app --reload --port 8000
```

Check:
- Health: `GET http://localhost:8000/health`
- API docs (FastAPI): `http://localhost:8000/docs`

---

## Frontend setup (Next.js)

### 1) Install deps
```bash
cd ../frontend
npm install
```

### 2) Configure API URL
Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3) Run the frontend
```bash
npm run dev
```

Open:
- `http://localhost:3000`

---

## How to use (EDGAR → Index → Chat)

### Step A — Ingest filings from EDGAR
The backend stores raw filings + parsed JSON locally:

```bash
# Example: ingest a ticker (10-K/10-Q depending on your request payload)
curl -X POST "http://localhost:8000/api/v1/edgar/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "filing_types": ["10-K", "10-Q"],
    "limit": 4
  }'
```

This returns a `task_id`. Poll status:

```bash
curl "http://localhost:8000/api/v1/edgar/status/<task_id>"
```

Artifacts written locally:
- `backend/data/filings/<TICKER>/<FORM>/<ACCESSION>.html`
- `backend/data/parsed/<TICKER>/<FORM>/<ACCESSION>.json`

> Ingestion **does not automatically index embeddings**. Indexing is a separate step.

---

### Step B — Index parsed filings into the vector store (Chroma)
Index a single ticker:

```bash
curl -X POST "http://localhost:8000/api/v1/retrieval/index" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL"
  }'
```

Or index everything under `backend/data/parsed`:

```bash
curl -X POST "http://localhost:8000/api/v1/retrieval/index-all"
```

Stats / sanity checks:
```bash
curl "http://localhost:8000/api/v1/retrieval/stats"
curl "http://localhost:8000/api/v1/retrieval/health"
```

Chroma persistence location:
- `backend/data/chroma`

---

### Step C — Chat with RAG enabled
In the UI (frontend), go to `/chat` and ask questions.

Or via cURL:

```bash
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session-1",
    "message": "Summarize risk factors discussed in the most recent 10-K.",
    "use_rag": true,
    "use_templates": true,
    "ticker_filter": "AAPL",
    "filing_type_filter": "10-K"
  }'
```

If retrieval finds relevant chunks, the response will include a **Sources** section.

---

## API overview

Base prefix:
- `/api/v1`

### Chat
- `POST /api/v1/chat/` — send a message (supports RAG + filters)
- `GET  /api/v1/chat/health` — LLM health check
- `POST /api/v1/chat/clear` — clear a session’s in-memory history

### EDGAR
- `POST /api/v1/edgar/ingest` — background ingestion task
- `GET  /api/v1/edgar/status/{task_id}` — check ingestion progress
- `GET  /api/v1/edgar/filings/{ticker}` — list locally stored filings
- `GET  /api/v1/edgar/filings/{ticker}/{accession}` — get parsed filing data

### Retrieval / Vector Search
- `POST /api/v1/retrieval/index` — chunk + embed + upsert a ticker’s parsed filings
- `POST /api/v1/retrieval/index-all` — index everything already parsed
- `POST /api/v1/retrieval/search` — semantic search (debug)
- `GET  /api/v1/retrieval/stats` — collection stats
- `GET  /api/v1/retrieval/stats/{ticker}` — stats by ticker
- `DELETE /api/v1/retrieval/{ticker}` — remove ticker docs from the vector store
- `GET  /api/v1/retrieval/health` — vector store health

---

## Architecture (current)

1. **Ingest**
   - Resolve CIK for ticker
   - Fetch filings list from SEC submissions API
   - Download filing HTML
   - Parse filing into sections (Item 1, 1A, 7, 8, etc.)
   - Save `data/filings` + `data/parsed`

2. **Index**
   - Chunk parsed sections with overlap
   - Embed with OpenAI embeddings
   - Upsert into ChromaDB with metadata

3. **Chat**
   - Optionally retrieve top chunks (with ticker/form filters)
   - Inject retrieved context into the prompt
   - Generate response via configured LLM provider
   - Append **Sources** (citations) when available

---

## Configuration notes

### SEC User-Agent is mandatory
The SEC requires a descriptive User-Agent string. Set:
```bash
SEC_USER_AGENT="Your Name your.email@domain.com"
```

### Embeddings are OpenAI-only (today)
Even if you use Ollama/Bedrock/HF for generation, indexing currently uses OpenAI embeddings.

### Data persistence
- Parsed filings and raw HTML persist under `backend/data/`
- Vectors persist under `backend/data/chroma`
- Chat history is **in-memory** by `session_id` (lost on server restart)

---

## Troubleshooting

### “No sources” / RAG not working
- Confirm you **indexed** after ingestion:
  - `POST /api/v1/retrieval/index` (or `/index-all`)
- Confirm vector store has docs:
  - `GET /api/v1/retrieval/stats`

### SEC request failures (403 / throttling)
- Ensure `SEC_USER_AGENT` is set and descriptive
- Slow down ingestion / reduce limits (avoid rapid repeated calls)
- Try again later; EDGAR endpoints rate limit aggressively

### Frontend can’t reach backend
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- Ensure backend is running on the port you configured

---

## Roadmap ideas
- XBRL extraction and deterministic KPI calculations (margin, liquidity, leverage)
- Multi-document comparisons (peer benchmarking)
- Evaluation harness (answer quality + citation correctness)
- Persistent chat history (DB-backed sessions)
- Auth + per-user workspaces (tickers, watchlists, notes)

---

## License
Add a license file if you intend for others to reuse this code.
