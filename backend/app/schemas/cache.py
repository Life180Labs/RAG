from pydantic import BaseModel


class CacheTypeStats(BaseModel):
    hits: int
    misses: int
    hit_ratio: float


class CacheStatsRead(BaseModel):
    retrieval: CacheTypeStats
    prompt: CacheTypeStats
    semantic: CacheTypeStats
    metadata: CacheTypeStats
