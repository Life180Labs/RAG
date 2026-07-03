import { apiGet, apiPatch, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { Repository, RepositoryActivityEntry, RepositorySettings } from '@/types/repository';

export const listRepositories = (projectId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Repository[]>>(`/projects/${projectId}/repositories`, signal);

export const getRepository = (repositoryId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Repository>>(`/repositories/${repositoryId}`, signal);

export const createRepository = (
  projectId: string,
  payload: { name: string; slug: string; description?: string },
) => apiPost<ApiSuccessResponse<Repository>>(`/projects/${projectId}/repositories`, payload);

export const updateRepository = (
  repositoryId: string,
  payload: { name: string; description?: string | null },
) => apiPatch<ApiSuccessResponse<Repository>>(`/repositories/${repositoryId}`, payload);

export const updateRepositorySettings = (repositoryId: string, payload: RepositorySettings) =>
  apiPatch<ApiSuccessResponse<Repository>>(`/repositories/${repositoryId}/settings`, payload);

export const archiveRepository = (repositoryId: string) =>
  apiPost<ApiSuccessResponse<Repository>>(`/repositories/${repositoryId}/archive`);

export const restoreRepository = (repositoryId: string) =>
  apiPost<ApiSuccessResponse<Repository>>(`/repositories/${repositoryId}/restore`);

export const getRepositoryActivity = (repositoryId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<RepositoryActivityEntry[]>>(
    `/repositories/${repositoryId}/activity`,
    signal,
  );
