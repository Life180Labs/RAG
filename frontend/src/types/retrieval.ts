export type SimilarityMetric = 'cosine' | 'dot' | 'euclidean';

export const SIMILARITY_METRICS: { value: SimilarityMetric; label: string }[] = [
  { value: 'cosine', label: 'Cosine (default)' },
  { value: 'dot', label: 'Dot product' },
  { value: 'euclidean', label: 'Euclidean' },
];

export type RetrievalStatus = 'pending' | 'completed' | 'failed';

export type RetrievalMode = 'dense' | 'hybrid';

export type FusionMethod = 'weighted_sum' | 'rrf' | 'rag_fusion';

export const FUSION_METHODS: { value: FusionMethod; label: string }[] = [
  { value: 'weighted_sum', label: 'Weighted sum' },
  { value: 'rrf', label: 'Reciprocal rank fusion' },
  { value: 'rag_fusion', label: 'RAG Fusion (requires query understanding)' },
];

export type RerankerProvider = 'cross_encoder' | 'bge' | 'flashrank' | 'cohere' | 'jina';

export const RERANKER_PROVIDERS: { value: RerankerProvider; label: string }[] = [
  { value: 'cross_encoder', label: 'Cross Encoder (MiniLM, local)' },
  { value: 'bge', label: 'BGE Reranker (local)' },
  { value: 'flashrank', label: 'FlashRank (local)' },
  { value: 'cohere', label: 'Cohere Rerank (cloud)' },
  { value: 'jina', label: 'Jina Reranker (cloud)' },
];

export type QueryIntent =
  | 'fact_lookup'
  | 'definition'
  | 'summarization'
  | 'comparison'
  | 'multi_hop_reasoning'
  | 'numerical_query'
  | 'code_question'
  | 'table_lookup'
  | 'policy_lookup'
  | 'conversational_followup';

export const QUERY_INTENT_LABELS: Record<QueryIntent, string> = {
  fact_lookup: 'Fact lookup',
  definition: 'Definition',
  summarization: 'Summarization',
  comparison: 'Comparison',
  multi_hop_reasoning: 'Multi-hop reasoning',
  numerical_query: 'Numerical query',
  code_question: 'Code question',
  table_lookup: 'Table lookup',
  policy_lookup: 'Policy lookup',
  conversational_followup: 'Conversational follow-up',
};

export interface Retrieval {
  id: string;
  vector_index_id: string;
  document_id: string;
  query_text: string;
  top_k: number;
  score_threshold: number | null;
  similarity_metric: SimilarityMetric;
  metadata_filter: Record<string, string> | null;
  retrieval_mode: RetrievalMode;
  fusion_method: FusionMethod | null;
  dense_weight: number | null;
  sparse_weight: number | null;
  rrf_k: number | null;
  query_understanding_enabled: boolean;
  query_intent: QueryIntent | null;
  intent_confidence: number | null;
  rewritten_query_text: string | null;
  generated_queries: string[] | null;
  detected_metadata_filter: Record<string, string> | null;
  expand_to_parent: boolean;
  use_mmr: boolean;
  mmr_lambda: number | null;
  compress_context: boolean;
  rerank_enabled: boolean;
  reranker_provider: RerankerProvider | null;
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
  dense_score: number | null;
  sparse_score: number | null;
  compressed_text: string | null;
  rerank_score: number | null;
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
  retrieval_mode?: RetrievalMode;
  fusion_method?: FusionMethod;
  dense_weight?: number;
  sparse_weight?: number;
  rrf_k?: number;
  query_understanding_enabled?: boolean;
  expand_to_parent?: boolean;
  use_mmr?: boolean;
  mmr_lambda?: number;
  compress_context?: boolean;
  rerank_enabled?: boolean;
  reranker_provider?: RerankerProvider;
}
