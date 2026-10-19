import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"
    
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "chroma_data")
    DOCS_DIR: str = str(BASE_DIR / "docs")
    DATA_DIR: str = str(BASE_DIR / "data")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
