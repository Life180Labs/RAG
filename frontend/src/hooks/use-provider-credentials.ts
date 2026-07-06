import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as providerCredentialService from '@/services/provider-credential-service';
import type { ProviderType } from '@/types/provider-credential';

export function useProviderCredentials(organizationId: string) {
  return useQuery({
    queryKey: ['organizations', organizationId, 'provider-credentials'],
    queryFn: ({ signal }) =>
      providerCredentialService.listProviderCredentials(organizationId, signal),
    select: (response) => response.data,
    enabled: Boolean(organizationId),
  });
}

export function useUpsertProviderCredential(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { provider: ProviderType; api_key: string }) =>
      providerCredentialService.upsertProviderCredential(organizationId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['organizations', organizationId, 'provider-credentials'],
      }),
  });
}

export function useDeleteProviderCredential(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (credentialId: string) =>
      providerCredentialService.deleteProviderCredential(organizationId, credentialId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['organizations', organizationId, 'provider-credentials'],
      }),
  });
}
