from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    # API Settings
    app_name: str = "MacroMap"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://macromap.ruthwikdovala.com",
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

    # Chat Settings
    max_history_length: int = 10
    max_tokens: int = 2048
    temperature: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
