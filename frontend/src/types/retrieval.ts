export type SimilarityMetric = 'cosine' | 'dot' | 'euclidean';

export const SIMILARITY_METRICS: { value: SimilarityMetric; label: string }[] = [
  { value: 'cosine', label: 'Cosine (default)' },
  { value: 'dot', label: 'Dot product' },
  { value: 'euclidean', label: 'Euclidean' },
];

export type RetrievalStatus = 'pending' | 'completed' | 'failed';

export interface Retrieval {
  id: string;
  vector_index_id: string;
  document_id: string;
  query_text: string;
  top_k: number;
  score_threshold: number | null;
  similarity_metric: SimilarityMetric;
  metadata_filter: Record<string, string> | null;
  status: RetrievalStatus;
  status_message: string | null;
  result_count: number;
  avg_similarity: number | null;
  min_similarity: number | null;
  max_similarity: number | null;
  latency_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface RetrievalResult {
  id: string;
  chunk_id: string;
  rank: number;
  score: number;
  chunk_text: string;
  chunk_heading: string | null;
  chunk_page: number | null;
}

export interface CreateRetrievalRequest {
  query_text: string;
  top_k?: number;
  score_threshold?: number | null;
  similarity_metric?: SimilarityMetric;
  metadata_filter?: Record<string, string> | null;
}
