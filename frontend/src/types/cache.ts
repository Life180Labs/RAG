export interface CacheTypeStats {
  hits: number;
  misses: number;
  hit_ratio: number;
}

export interface CacheStats {
  retrieval: CacheTypeStats;
  prompt: CacheTypeStats;
  semantic: CacheTypeStats;
  metadata: CacheTypeStats;
}
