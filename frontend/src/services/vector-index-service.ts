import { apiDelete, apiGet, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { VectorIndex } from '@/types/vector-index';

const basePath = (documentId: string, chunkSetId: string, embeddingVersionId: string) =>
  `/documents/${documentId}/chunk-sets/${chunkSetId}/embeddings/${embeddingVersionId}/index`;

export const listVectorIndexes = (
  documentId: string,
  chunkSetId: string,
  embeddingVersionId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<VectorIndex[]>>(
    basePath(documentId, chunkSetId, embeddingVersionId),
    signal,
  );

export const createOrRebuildIndex = (
  documentId: string,
  chunkSetId: string,
  embeddingVersionId: string,
  provider: string,
  indexType: string,
) =>
  apiPost<ApiSuccessResponse<{ enqueued: boolean; provider: string; index_type: string }>>(
    basePath(documentId, chunkSetId, embeddingVersionId),
    { provider, index_type: indexType },
  );

export const deleteVectorIndex = (
  documentId: string,
  chunkSetId: string,
  embeddingVersionId: string,
  vectorIndexId: string,
) =>
  apiDelete<ApiSuccessResponse<{ enqueued: boolean }>>(
    `${basePath(documentId, chunkSetId, embeddingVersionId)}/${vectorIndexId}`,
  );
