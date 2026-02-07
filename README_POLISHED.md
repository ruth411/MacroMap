# MacroMap

A financial analyst copilot that transforms SEC EDGAR filings into an intelligent, searchable knowledge base. Ask questions about 10-K and 10-Q filings through a conversational interface powered by RAG (Retrieval-Augmented Generation).

**Live Demo:** [macromap.ruthwikdovala.com](https://macromap.ruthwikdovala.com)

---

## Features

- **SEC Filing Ingestion** — Automatically download and parse 10-K/10-Q filings from EDGAR
- **Intelligent Search** — Hybrid search combining semantic embeddings with keyword matching
- **RAG-Powered Chat** — Answers grounded in actual SEC filings with source citations
- **Query Expansion** — Automatically generates related queries for comprehensive retrieval
- **Cross-Encoder Reranking** — Improves result relevance using neural reranking
- **Multi-Provider LLM Support** — OpenAI, Ollama, AWS Bedrock, HuggingFace
- **User Authentication** — Secure JWT-based auth with Google OAuth support
- **Rate Limiting** — Protection against API abuse
- **Production Ready** — Deployed on Railway (backend) + Vercel (frontend)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11 |
| **Database** | PostgreSQL (users/sessions), ChromaDB (vectors) |
| **Embeddings** | OpenAI `text-embedding-3-small` |
| **Reranking** | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **Auth** | JWT with httpOnly cookies, Google OAuth |
| **Deployment** | Railway (API), Vercel (UI) |

---

## Architecture

```
┌─────────────────┐     ┌─────────────────────────────────────────┐
│                 │     │              Backend (FastAPI)          │
│   Next.js UI    │────▶│                                         │
│   (Vercel)      │     │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│                 │◀────│  │  Auth   │  │  Chat   │  │  EDGAR  │ │
└─────────────────┘     │  └────┬────┘  └────┬────┘  └────┬────┘ │
                        │       │            │            │       │
                        │       ▼            ▼            ▼       │
                        │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
                        │  │PostgreSQL│  │ChromaDB │  │SEC EDGAR│ │
                        │  │(Users)  │  │(Vectors)│  │  (API)  │ │
                        │  └─────────┘  └─────────┘  └─────────┘ │
                        └─────────────────────────────────────────┘
```

### RAG Pipeline

1. **Query Expansion** — Generate 3 related queries for broader coverage
2. **Hybrid Search** — Combine semantic (embeddings) + keyword (BM25) search
3. **Cross-Encoder Reranking** — Rerank results for precision
4. **Context Assembly** — Build prompt with retrieved chunks
5. **Generation** — LLM generates answer with inline citations

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key
- PostgreSQL (or use SQLite for local dev)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your keys
```

**Required environment variables:**

```env
# SEC EDGAR (required for ingestion)
SEC_USER_AGENT="YourName your.email@domain.com"

# OpenAI (required for embeddings)
OPENAI_API_KEY="sk-..."

# Database
DATABASE_URL="postgresql://user:pass@localhost/macromap"

# Auth
JWT_SECRET="your-secure-random-string"

# Optional: LLM provider
LLM_PROVIDER="openai"  # openai | ollama | bedrock | huggingface
```

**Run the server:**

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Usage

### 1. Ingest SEC Filings

```bash
curl -X POST "http://localhost:8000/api/v1/edgar/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "filing_types": ["10-K", "10-Q"],
    "limit": 4
  }'
```

### 2. Index for Search

```bash
# Index a specific ticker
curl -X POST "http://localhost:8000/api/v1/retrieval/index" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'

# Or index all parsed filings
curl -X POST "http://localhost:8000/api/v1/retrieval/index-all"
```

### 3. Chat with RAG

```bash
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are Apple'\''s main risk factors?",
    "use_rag": true,
    "ticker_filter": "AAPL"
  }'
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create new account |
| POST | `/api/v1/auth/login` | Login with email/password |
| POST | `/api/v1/auth/google` | Google OAuth login |
| POST | `/api/v1/auth/logout` | Logout (clears cookie) |
| GET | `/api/v1/auth/me` | Get current user |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/` | Send message (RAG-enabled) |
| POST | `/api/v1/chat/sessions` | Create chat session |
| GET | `/api/v1/chat/sessions` | List user sessions |
| GET | `/api/v1/chat/sessions/{id}` | Get session with messages |

### EDGAR
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/edgar/ingest` | Start ingestion task |
| GET | `/api/v1/edgar/status/{task_id}` | Check task status |
| GET | `/api/v1/edgar/filings/{ticker}` | List stored filings |

### Retrieval
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/retrieval/index` | Index a ticker's filings |
| POST | `/api/v1/retrieval/index-all` | Index all parsed filings |
| POST | `/api/v1/retrieval/search` | Direct semantic search |
| GET | `/api/v1/retrieval/stats` | Collection statistics |

---

## Project Structure

```
MacroMap/
├── backend/
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── core/          # Config, auth, database
│   │   ├── models/        # SQLAlchemy models
│   │   └── services/      # Business logic
│   │       ├── edgar/     # SEC filing ingestion
│   │       ├── llm/       # LLM providers & prompts
│   │       └── retrieval/ # RAG pipeline
│   ├── data/              # Local storage
│   │   ├── filings/       # Raw HTML
│   │   ├── parsed/        # Parsed JSON
│   │   └── chroma/        # Vector store
│   └── tests/             # Integration tests
├── frontend/
│   ├── app/               # Next.js app router
│   ├── components/        # React components
│   └── lib/               # API client, utilities
└── scripts/               # Utility scripts
```

---

## Deployment

### Backend (Railway)

1. Connect your GitHub repo to Railway
2. Set the root directory to `backend`
3. Add environment variables in Railway dashboard
4. Deploy — Railway auto-detects the Dockerfile

### Frontend (Vercel)

1. Import project to Vercel
2. Set root directory to `frontend`
3. Add `NEXT_PUBLIC_API_URL` pointing to your Railway backend
4. Deploy

---

## Security Features

- **httpOnly Cookies** — JWT tokens stored securely, immune to XSS
- **CORS Configuration** — Strict origin validation
- **Rate Limiting** — Prevents API abuse (slowapi)
- **Password Hashing** — bcrypt with salt
- **Input Validation** — Pydantic models for all inputs

---

## Reducing Hallucinations

MacroMap uses several techniques to ground responses in facts:

1. **RAG Pipeline** — Every answer draws from actual SEC filings
2. **Source Citations** — Responses include document references
3. **Query Expansion** — Multiple search queries improve recall
4. **Cross-Encoder Reranking** — Better precision in retrieved context
5. **Structured Prompts** — LLM instructed to cite sources and acknowledge uncertainty

---

## Testing

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_chat.py -v
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- SEC EDGAR for public filing data
- OpenAI for embeddings and language models
- ChromaDB for vector storage
- The FastAPI and Next.js communities
