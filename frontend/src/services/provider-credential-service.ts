import { apiDelete, apiGet, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { ProviderCredential, ProviderType } from '@/types/provider-credential';

export const listProviderCredentials = (organizationId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<ProviderCredential[]>>(
    `/organizations/${organizationId}/provider-credentials`,
    signal,
  );

export const upsertProviderCredential = (
  organizationId: string,
  payload: { provider: ProviderType; api_key: string },
) =>
  apiPost<ApiSuccessResponse<ProviderCredential>>(
    `/organizations/${organizationId}/provider-credentials`,
    payload,
  );

export const deleteProviderCredential = (organizationId: string, credentialId: string) =>
  apiDelete<ApiSuccessResponse<{ deleted: boolean }>>(
    `/organizations/${organizationId}/provider-credentials/${credentialId}`,
  );
