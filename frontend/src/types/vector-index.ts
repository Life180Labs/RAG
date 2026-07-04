export type VectorIndexProviderName = 'pgvector' | 'qdrant' | 'chroma' | 'pinecone';

export const VECTOR_INDEX_PROVIDERS: { value: VectorIndexProviderName; label: string }[] = [
  { value: 'pgvector', label: 'PgVector (default)' },
  { value: 'qdrant', label: 'Qdrant' },
  { value: 'chroma', label: 'Chroma' },
  { value: 'pinecone', label: 'Pinecone' },
];

export type VectorIndexType = 'hnsw' | 'ivf_flat' | 'flat' | 'pq';

export const VECTOR_INDEX_TYPES: { value: VectorIndexType; label: string }[] = [
  { value: 'hnsw', label: 'HNSW' },
  { value: 'ivf_flat', label: 'IVF Flat' },
  { value: 'flat', label: 'Flat (exact)' },
  { value: 'pq', label: 'Product quantization' },
];

export type VectorIndexStatus = 'pending' | 'building' | 'ready' | 'failed';

export interface VectorIndex {
  id: string;
  embedding_version_id: string;
  document_id: string;
  provider: string;
  index_type: string;
  namespace: string;
  dimensions: number;
  version: number;
  status: VectorIndexStatus;
  status_message: string | null;
  vector_count: number;
  build_duration_ms: number | null;
  created_at: string;
  updated_at: string;
}
