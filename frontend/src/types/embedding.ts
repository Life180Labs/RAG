export type EmbeddingProviderName = 'bge' | 'e5' | 'nomic' | 'openai' | 'voyage' | 'jina';

export const EMBEDDING_PROVIDERS: { value: EmbeddingProviderName; label: string }[] = [
  { value: 'bge', label: 'BGE (local, default)' },
  { value: 'e5', label: 'E5 (local)' },
  { value: 'nomic', label: 'Nomic (local)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'voyage', label: 'Voyage' },
  { value: 'jina', label: 'Jina' },
];

export type EmbeddingVersionStatus = 'pending' | 'ready' | 'failed';
export type EmbeddingStatus = 'ready' | 'failed';

export interface EmbeddingVersion {
  id: string;
  chunk_set_id: string;
  document_id: string;
  provider: string;
  model: string;
  dimensions: number;
  version: number;
  status: EmbeddingVersionStatus;
  status_message: string | null;
  embedding_count: number;
  total_tokens: number;
  total_cost_usd: number | null;
  avg_latency_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface Embedding {
  id: string;
  embedding_version_id: string;
  chunk_id: string;
  token_count: number;
  cost_usd: number | null;
  latency_ms: number;
  status: EmbeddingStatus;
  status_message: string | null;
}

export interface EmbeddingVersionComparison {
  version_a: EmbeddingVersion;
  embeddings_a: Embedding[];
  version_b: EmbeddingVersion;
  embeddings_b: Embedding[];
}
