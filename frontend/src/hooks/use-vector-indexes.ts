import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as vectorIndexService from '@/services/vector-index-service';

export function useVectorIndexes(
  documentId: string,
  chunkSetId: string,
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
      'index',
    ],
    queryFn: ({ signal }) =>
      vectorIndexService.listVectorIndexes(
        documentId,
        chunkSetId,
        embeddingVersionId as string,
        signal,
      ),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(chunkSetId) && Boolean(embeddingVersionId),
  });
}

export function useCreateOrRebuildIndex(
  documentId: string,
  chunkSetId: string,
  embeddingVersionId: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ provider, indexType }: { provider: string; indexType: string }) =>
      vectorIndexService.createOrRebuildIndex(
        documentId,
        chunkSetId,
        embeddingVersionId,
        provider,
        indexType,
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: [
          'documents',
          documentId,
          'chunk-sets',
          chunkSetId,
          'embeddings',
          embeddingVersionId,
          'index',
        ],
      }),
  });
}

export function useDeleteVectorIndex(
  documentId: string,
  chunkSetId: string,
  embeddingVersionId: string,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vectorIndexId: string) =>
      vectorIndexService.deleteVectorIndex(
        documentId,
        chunkSetId,
        embeddingVersionId,
        vectorIndexId,
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: [
          'documents',
          documentId,
          'chunk-sets',
          chunkSetId,
          'embeddings',
          embeddingVersionId,
          'index',
        ],
      }),
  });
}
