from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # API Settings
    app_name: str = "MacroMap"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # OpenAI
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    openai_chat_model_large: str = "gpt-4o"

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent.parent
    data_dir: Path = base_dir / "data"
    filings_dir: Path = data_dir / "filings"
    parsed_dir: Path = data_dir / "parsed"
    chroma_dir: Path = data_dir / "chroma"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/macromap.db"

    # SEC EDGAR
    sec_user_agent: str = "MacroMap research@example.com"
    sec_rate_limit: float = 0.1  # 10 requests per second max

    # ChromaDB
    chroma_collection_name: str = "sec_filings"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
