import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as chunkService from '@/services/chunk-service';

export function useChunkSets(documentId: string) {
  return useQuery({
    queryKey: ['documents', documentId, 'chunk-sets'],
    queryFn: ({ signal }) => chunkService.listChunkSets(documentId, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId),
  });
}

export function useChunks(documentId: string, chunkSetId: string | null) {
  return useQuery({
    queryKey: ['documents', documentId, 'chunk-sets', chunkSetId, 'chunks'],
    queryFn: ({ signal }) => chunkService.listChunks(documentId, chunkSetId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(chunkSetId),
  });
}

export function useCompareChunkSets(
  documentId: string,
  strategyA: string | null,
  strategyB: string | null,
) {
  return useQuery({
    queryKey: ['documents', documentId, 'chunk-sets', 'compare', strategyA, strategyB],
    queryFn: ({ signal }) =>
      chunkService.compareChunkSets(documentId, strategyA as string, strategyB as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(strategyA) && Boolean(strategyB),
  });
}

export function useGenerateChunks(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (strategy: string) => chunkService.generateChunks(documentId, strategy),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['documents', documentId, 'chunk-sets'] }),
  });
}

export function useDeleteChunkSet(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (chunkSetId: string) => chunkService.deleteChunkSet(documentId, chunkSetId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['documents', documentId, 'chunk-sets'] }),
  });
}
