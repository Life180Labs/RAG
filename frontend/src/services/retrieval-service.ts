import { apiGet, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { CreateRetrievalRequest, Retrieval, RetrievalResult } from '@/types/retrieval';

const basePath = (documentId: string, vectorIndexId: string) =>
  `/documents/${documentId}/vector-indexes/${vectorIndexId}/retrievals`;

export const listRetrievals = (documentId: string, vectorIndexId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Retrieval[]>>(basePath(documentId, vectorIndexId), signal);

export const getRetrieval = (
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<Retrieval>>(
    `${basePath(documentId, vectorIndexId)}/${retrievalId}`,
    signal,
  );

export const getRetrievalResults = (
  documentId: string,
  vectorIndexId: string,
  retrievalId: string,
  signal?: AbortSignal,
) =>
  apiGet<ApiSuccessResponse<RetrievalResult[]>>(
    `${basePath(documentId, vectorIndexId)}/${retrievalId}/results`,
    signal,
  );

export const createRetrieval = (
  documentId: string,
  vectorIndexId: string,
  payload: CreateRetrievalRequest,
) => apiPost<ApiSuccessResponse<Retrieval>>(basePath(documentId, vectorIndexId), payload);
