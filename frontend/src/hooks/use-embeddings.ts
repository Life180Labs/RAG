import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as embeddingService from '@/services/embedding-service';

export function useEmbeddingVersions(documentId: string, chunkSetId: string | null) {
  return useQuery({
    queryKey: ['documents', documentId, 'chunk-sets', chunkSetId, 'embeddings'],
    queryFn: ({ signal }) =>
      embeddingService.listEmbeddingVersions(documentId, chunkSetId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(chunkSetId),
  });
}

export function useEmbeddings(
  documentId: string,
  chunkSetId: string | null,
  embeddingVersionId: string | null,
) {
  return useQuery({
    queryKey: [
      'documents',
      documentId,
      'chunk-sets',
      chunkSetId,
      'embeddings',
      embeddingVersionId,
      'vectors',
    ],
    queryFn: ({ signal }) =>
      embeddingService.listEmbeddings(
        documentId,
        chunkSetId as string,
        embeddingVersionId as string,
        signal,
      ),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(chunkSetId) && Boolean(embeddingVersionId),
  });
}

export function useCompareEmbeddingVersions(
  documentId: string,
  chunkSetId: string | null,
  providerA: string | null,
  providerB: string | null,
) {
  return useQuery({
    queryKey: [
      'documents',
      documentId,
      'chunk-sets',
      chunkSetId,
      'embeddings',
      'compare',
      providerA,
      providerB,
    ],
    queryFn: ({ signal }) =>
      embeddingService.compareEmbeddingVersions(
        documentId,
        chunkSetId as string,
        providerA as string,
        providerB as string,
        signal,
      ),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(chunkSetId) && Boolean(providerA) && Boolean(providerB),
  });
}

export function useGenerateEmbeddings(documentId: string, chunkSetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) =>
      embeddingService.generateEmbeddings(documentId, chunkSetId, provider),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['documents', documentId, 'chunk-sets', chunkSetId, 'embeddings'],
      }),
  });
}

export function useDeleteEmbeddingVersion(documentId: string, chunkSetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (embeddingVersionId: string) =>
      embeddingService.deleteEmbeddingVersion(documentId, chunkSetId, embeddingVersionId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['documents', documentId, 'chunk-sets', chunkSetId, 'embeddings'],
      }),
  });
}
