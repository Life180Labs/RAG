import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as repositoryService from '@/services/repository-service';
import type { RepositorySettings } from '@/types/repository';

export function useRepositories(projectId: string) {
  return useQuery({
    queryKey: ['projects', projectId, 'repositories'],
    queryFn: ({ signal }) => repositoryService.listRepositories(projectId, signal),
    select: (response) => response.data,
    enabled: Boolean(projectId),
  });
}

export function useRepository(repositoryId: string) {
  return useQuery({
    queryKey: ['repositories', repositoryId],
    queryFn: ({ signal }) => repositoryService.getRepository(repositoryId, signal),
    select: (response) => response.data,
    enabled: Boolean(repositoryId),
  });
}

export function useCreateRepository(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; slug: string; description?: string }) =>
      repositoryService.createRepository(projectId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['projects', projectId, 'repositories'] }),
  });
}

export function useUpdateRepositorySettings(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RepositorySettings) =>
      repositoryService.updateRepositorySettings(repositoryId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['repositories', repositoryId] }),
  });
}

export function useRepositoryActivity(repositoryId: string) {
  return useQuery({
    queryKey: ['repositories', repositoryId, 'activity'],
    queryFn: ({ signal }) => repositoryService.getRepositoryActivity(repositoryId, signal),
    select: (response) => response.data,
    enabled: Boolean(repositoryId),
  });
}
