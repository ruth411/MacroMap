from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    # API Settings
    app_name: str = "MacroMap"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # CORS - Allow frontend domains to access the API
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://macromap.ruthwikdovala.com",
        "https://www.macromap.ruthwikdovala.com",
        "https://macro-map-xi.vercel.app",
    ]

    # LLM Provider Settings
    llm_provider: Literal["openai", "ollama", "bedrock", "huggingface"] = "openai"

    # OpenAI Settings (recommended)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Ollama Settings (local development)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # AWS Bedrock Settings (production)
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "meta.llama3-8b-instruct-v1:0"

    # Hugging Face Settings (alternative)
    hf_model_id: str = "microsoft/phi-3-mini-4k-instruct"
    hf_api_token: str = ""

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent.parent
    data_dir: Path = base_dir / "data"
    filings_dir: Path = data_dir / "filings"
    parsed_dir: Path = data_dir / "parsed"
    chroma_dir: Path = data_dir / "chroma"

    # Database: Set DATABASE_URL env var for PostgreSQL (Railway provides this)
    # Falls back to SQLite in data directory for local development
    database_url: str = ""

    @property
    def effective_database_url(self) -> str:
        """Get the database URL, with fallback to SQLite in data dir."""
        import os
        if self.database_url:
            return self.database_url
        # Use data directory for SQLite (works on both Unix and Windows)
        db_path = self.data_dir / "macromap.db"
        return f"sqlite+aiosqlite:///{db_path}"

    # SEC EDGAR
    sec_user_agent: str = "MacroMap research@example.com"
    sec_rate_limit: float = 0.1  # 10 requests per second max

    # ChromaDB
    chroma_collection_name: str = "sec_filings"

    # Chunking - smaller chunks for better precision
    chunk_size: int = 512
    chunk_overlap: int = 100

    # RAG Reranking Settings
    reranker_enabled: bool = True
    reranker_type: str = "cross-encoder"  # "cross-encoder", "cohere", "none"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_k: int = 5  # Final number of results after reranking
    retrieval_initial_k: int = 20  # Initial retrieval before reranking (increased for hybrid)

    # RAG Query Expansion Settings
    query_expansion_enabled: bool = True  # Use LLM to expand queries with related terms

    # RAG Hybrid Search Settings
    hybrid_search_enabled: bool = True  # Combine vector + BM25 keyword search
    hybrid_vector_weight: float = 0.7  # Weight for vector search results
    hybrid_bm25_weight: float = 0.3  # Weight for BM25 results

    # Chat Settings
    max_history_length: int = 10
    max_tokens: int = 2048
    temperature: float = 0.7

    # Authentication
    # IMPORTANT: Set JWT_SECRET_KEY env var in production!
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    @property
    def effective_jwt_secret(self) -> str:
        """Get JWT secret, with fallback for development only."""
        if self.jwt_secret_key:
            return self.jwt_secret_key
        if self.debug:
            # Only allow default in debug mode
            return "dev-only-secret-do-not-use-in-production"
        raise ValueError(
            "JWT_SECRET_KEY must be set in production! "
            "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"  # Default for general endpoints
    rate_limit_auth: str = "5/minute"  # Stricter for auth endpoints (login, register)
    rate_limit_chat: str = "20/minute"  # Chat endpoints
    rate_limit_ingestion: str = "10/minute"  # EDGAR ingestion (heavy operations)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
