import { apiDelete, apiGet, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { Chunk, ChunkSet, ChunkSetComparison } from '@/types/chunk';

export const listChunkSets = (documentId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<ChunkSet[]>>(`/documents/${documentId}/chunk-sets`, signal);

export const listChunks = (documentId: string, chunkSetId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Chunk[]>>(
    `/documents/${documentId}/chunk-sets/${chunkSetId}/chunks`,
    signal,
  );

export const compareChunkSets = (
  documentId: string,
  strategyA: string,
  strategyB: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<ChunkSetComparison>>(
    `/documents/${documentId}/chunk-sets/compare?strategy_a=${encodeURIComponent(
      strategyA,
    )}&strategy_b=${encodeURIComponent(strategyB)}`,
    signal,
  );

export const generateChunks = (documentId: string, strategy: string) =>
  apiPost<ApiSuccessResponse<{ enqueued: boolean; strategy: string }>>(
    `/documents/${documentId}/chunk-sets`,
    { strategy },
  );

export const deleteChunkSet = (documentId: string, chunkSetId: string) =>
  apiDelete<ApiSuccessResponse<{ deleted: boolean }>>(
    `/documents/${documentId}/chunk-sets/${chunkSetId}`,
  );
