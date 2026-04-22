from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os


load_dotenv()


class Settings(BaseModel):
    app_name: str = "Role-Based Internal RAG Chatbot"
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-for-production")
    token_expire_minutes: int = int(os.getenv("TOKEN_EXPIRE_MINUTES", "120"))
    top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    min_relevance_score: float = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.2"))
    vector_store_provider: str = os.getenv("VECTOR_STORE_PROVIDER", "chroma").strip().lower()
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "company_documents_hf")
    pinecone_api_key: str | None = os.getenv("PINECONE_API_KEY")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "role-based-ragchatbot")
    pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE", "company-docs")
    pinecone_cloud: str = os.getenv("PINECONE_CLOUD", "aws")
    pinecone_region: str = os.getenv("PINECONE_REGION", "us-east-1")
    pinecone_dimension: int = int(os.getenv("PINECONE_DIMENSION", "1024"))
    pinecone_metric: str = os.getenv("PINECONE_METRIC", "cosine")
    huggingfacehub_api_token: str | None = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    hf_embedding_model: str = os.getenv(
        "HF_EMBEDDING_MODEL",
        "sentence-transformers/all-mpnet-base-v2",
    )
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def data_dir(self) -> Path:
        return self.project_root / "resources" / "data"

    @property
    def vector_store_dir(self) -> Path:
        return self.project_root / "resources" / "vectorstore" / "chroma"


@lru_cache
def get_settings() -> Settings:
    return Settings()
