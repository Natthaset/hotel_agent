import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # Ollama settings
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

    # Qdrant settings
    qdrant_host: str = os.getenv("QDRANT_HOST", "qdrant-db")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "hotel_policies")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

    # .NET API settings
    dotnet_api_url: str = os.getenv("DOTNET_API_URL", "http://dotnet-api:8080")

    # Service settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

settings = Settings()
