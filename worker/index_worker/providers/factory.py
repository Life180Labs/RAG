"""Vector index provider factory (docs/05-task.md Phase 8).

PgVector needs the same sync SQLAlchemy session the calling task already
holds (its "index" lives in the same Postgres database as the vectors);
the other providers are standalone HTTP clients. Weaviate and Milvus are
not implemented — see docs/03-database.md section 18 for why.
"""

from sqlalchemy.orm import Session

from common.config import get_worker_settings
from index_worker.providers.base import VectorIndexProvider
from index_worker.providers.chroma_provider import ChromaProvider
from index_worker.providers.pgvector_provider import PgVectorProvider
from index_worker.providers.pinecone_provider import PineconeProvider
from index_worker.providers.qdrant_provider import QdrantProvider

DEFAULT_PROVIDER = "pgvector"
DEFAULT_INDEX_TYPE = "hnsw"

_KNOWN_PROVIDERS = {"pgvector", "qdrant", "chroma", "pinecone"}


def get_provider(provider: str, session: Session) -> VectorIndexProvider:
    if provider not in _KNOWN_PROVIDERS:
        raise ValueError(f"Unknown vector index provider '{provider}'.")

    if provider == "pgvector":
        return PgVectorProvider(session)

    settings = get_worker_settings()
    if provider == "qdrant":
        return QdrantProvider(settings.qdrant_url)
    if provider == "chroma":
        return ChromaProvider(settings.chroma_url)
    return PineconeProvider(settings.pinecone_api_key)
