import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as retrievalService from '@/services/retrieval-service';
import type { CreateRetrievalRequest } from '@/types/retrieval';

export function useRetrievals(documentId: string, vectorIndexId: string | null) {
  return useQuery({
    queryKey: ['documents', documentId, 'vector-indexes', vectorIndexId, 'retrievals'],
    queryFn: ({ signal }) =>
      retrievalService.listRetrievals(documentId, vectorIndexId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(vectorIndexId),
  });
}

export function useRetrieval(
  documentId: string,
  vectorIndexId: string,
  retrievalId: string | null,
) {
  return useQuery({
    queryKey: ['documents', documentId, 'vector-indexes', vectorIndexId, 'retrievals', retrievalId],
    queryFn: ({ signal }) =>
      retrievalService.getRetrieval(documentId, vectorIndexId, retrievalId as string, signal),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(vectorIndexId) && Boolean(retrievalId),
    // Retrieval execution is async (backend creates the row PENDING, then
    // retrieval_worker fills it in) — poll until it leaves PENDING, the
    // same "make the async pipeline feel responsive" need every other
    // explorer has, just not yet solved with polling before this phase.
    refetchInterval: (query) => (query.state.data?.data.status === 'pending' ? 500 : false),
  });
}

export function useRetrievalResults(
  documentId: string,
  vectorIndexId: string,
  retrievalId: string | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: [
      'documents',
      documentId,
      'vector-indexes',
      vectorIndexId,
      'retrievals',
      retrievalId,
      'results',
    ],
    queryFn: ({ signal }) =>
      retrievalService.getRetrievalResults(
        documentId,
        vectorIndexId,
        retrievalId as string,
        signal,
      ),
    select: (response) => response.data,
    enabled: Boolean(documentId) && Boolean(vectorIndexId) && Boolean(retrievalId) && enabled,
  });
}

export function useCreateRetrieval(documentId: string, vectorIndexId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateRetrievalRequest) =>
      retrievalService.createRetrieval(documentId, vectorIndexId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['documents', documentId, 'vector-indexes', vectorIndexId, 'retrievals'],
      }),
  });
}
