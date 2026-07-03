import type { ResourceStatus } from '@/types/tenancy';

export interface Repository {
  id: string;
  project_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: ResourceStatus;
  default_chunk_strategy: string | null;
  default_embedding_model: string | null;
  default_retriever: string | null;
  default_reranker: string | null;
  default_prompt_version: string | null;
  document_count: number;
  chunk_count: number;
  embedding_count: number;
  storage_used_bytes: number;
  retrieval_count: number;
  created_at: string;
  updated_at: string;
}

export interface RepositoryActivityEntry {
  action: string;
  result: string;
  created_at: string;
}

export interface RepositorySettings {
  default_chunk_strategy: string | null;
  default_embedding_model: string | null;
  default_retriever: string | null;
  default_reranker: string | null;
  default_prompt_version: string | null;
}
