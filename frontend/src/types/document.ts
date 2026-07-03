export type DocumentStatus =
  | 'uploaded'
  | 'validating'
  | 'validated'
  | 'parsing'
  | 'ocr'
  | 'cleaning'
  | 'chunking'
  | 'embedding'
  | 'indexing'
  | 'ready'
  | 'failed_upload'
  | 'failed_validation'
  | 'failed_parse'
  | 'failed_ocr'
  | 'failed_chunk'
  | 'failed_embed'
  | 'failed_index';

export interface Document {
  id: string;
  repository_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256_hash: string;
  status: DocumentStatus;
  status_message: string | null;
  current_version: number;
  language: string | null;
  page_count: number | null;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: string;
  version: number;
  filename: string;
  size_bytes: number;
  sha256_hash: string;
  status: DocumentStatus;
  created_at: string;
}

export interface DownloadResponse {
  url: string | null;
  stream_via_backend: boolean;
}
