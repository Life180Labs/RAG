export type ChunkStrategy =
  | 'fixed'
  | 'sliding_window'
  | 'recursive'
  | 'paragraph'
  | 'sentence'
  | 'markdown'
  | 'html'
  | 'semantic'
  | 'parent_child'
  | 'hierarchical'
  | 'adaptive';

export const CHUNK_STRATEGIES: { value: ChunkStrategy; label: string }[] = [
  { value: 'recursive', label: 'Recursive (default)' },
  { value: 'fixed', label: 'Fixed size' },
  { value: 'sliding_window', label: 'Sliding window' },
  { value: 'paragraph', label: 'Paragraph' },
  { value: 'sentence', label: 'Sentence' },
  { value: 'markdown', label: 'Markdown (structural)' },
  { value: 'html', label: 'HTML (structural)' },
  { value: 'semantic', label: 'Semantic' },
  { value: 'parent_child', label: 'Parent/child' },
  { value: 'hierarchical', label: 'Hierarchical' },
  { value: 'adaptive', label: 'Adaptive' },
];

export type ChunkSetStatus = 'pending' | 'ready' | 'failed';
export type ChunkStatus = 'ready' | 'failed' | 'skipped';

export interface ChunkSet {
  id: string;
  document_id: string;
  version: number;
  strategy: string;
  config: Record<string, unknown>;
  status: ChunkSetStatus;
  status_message: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface Chunk {
  id: string;
  chunk_set_id: string;
  parent_chunk_id: string | null;
  chunk_index: number;
  text: string;
  char_start: number;
  char_end: number;
  token_count: number;
  page: number | null;
  heading: string | null;
  language: string | null;
  status: ChunkStatus;
  status_message: string | null;
  embedding_model: string | null;
}

export interface ChunkSetComparison {
  strategy_a: ChunkSet;
  chunks_a: Chunk[];
  strategy_b: ChunkSet;
  chunks_b: Chunk[];
}
