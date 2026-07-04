import { apiDelete, apiGet, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { Embedding, EmbeddingVersion, EmbeddingVersionComparison } from '@/types/embedding';

export const listEmbeddingVersions = (
  documentId: string,
  chunkSetId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<EmbeddingVersion[]>>(
    `/documents/${documentId}/chunk-sets/${chunkSetId}/embeddings`,
    signal,
  );

export const listEmbeddings = (
  documentId: string,
  chunkSetId: string,
  embeddingVersionId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<Embedding[]>>(
    `/documents/${documentId}/chunk-sets/${chunkSetId}/embeddings/${embeddingVersionId}/vectors`,
    signal,
  );

export const compareEmbeddingVersions = (
  documentId: string,
  chunkSetId: string,
  providerA: string,
  providerB: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<EmbeddingVersionComparison>>(
    `/documents/${documentId}/chunk-sets/${chunkSetId}/embeddings/compare?provider_a=${encodeURIComponent(
      providerA,
    )}&provider_b=${encodeURIComponent(providerB)}`,
    signal,
  );

export const generateEmbeddings = (documentId: string, chunkSetId: string, provider: string) =>
  apiPost<ApiSuccessResponse<{ enqueued: boolean; provider: string; model: string | null }>>(
    `/documents/${documentId}/chunk-sets/${chunkSetId}/embeddings`,
    { provider },
  );

export const deleteEmbeddingVersion = (
  documentId: string,
  chunkSetId: string,
  embeddingVersionId: string,
) =>
  apiDelete<ApiSuccessResponse<{ deleted: boolean }>>(
    `/documents/${documentId}/chunk-sets/${chunkSetId}/embeddings/${embeddingVersionId}`,
  );
