import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as tenancyService from '@/services/tenancy-service';
import type { MemberRole } from '@/types/tenancy';

export function useOrganizations() {
  return useQuery({
    queryKey: ['organizations'],
    queryFn: ({ signal }) => tenancyService.listOrganizations(signal),
    select: (response) => response.data,
  });
}

export function useOrganization(organizationId: string) {
  return useQuery({
    queryKey: ['organizations', organizationId],
    queryFn: ({ signal }) => tenancyService.getOrganization(organizationId, signal),
    select: (response) => response.data,
    enabled: Boolean(organizationId),
  });
}

export function useCreateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: tenancyService.createOrganization,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['organizations'] }),
  });
}

export function useWorkspaces(organizationId: string) {
  return useQuery({
    queryKey: ['organizations', organizationId, 'workspaces'],
    queryFn: ({ signal }) => tenancyService.listWorkspaces(organizationId, signal),
    select: (response) => response.data,
    enabled: Boolean(organizationId),
  });
}

export function useWorkspace(workspaceId: string) {
  return useQuery({
    queryKey: ['workspaces', workspaceId],
    queryFn: ({ signal }) => tenancyService.getWorkspace(workspaceId, signal),
    select: (response) => response.data,
    enabled: Boolean(workspaceId),
  });
}

export function useCreateWorkspace(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; slug: string }) =>
      tenancyService.createWorkspace(organizationId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['organizations', organizationId, 'workspaces'],
      }),
  });
}

export function useProjects(workspaceId: string) {
  return useQuery({
    queryKey: ['workspaces', workspaceId, 'projects'],
    queryFn: ({ signal }) => tenancyService.listProjects(workspaceId, signal),
    select: (response) => response.data,
    enabled: Boolean(workspaceId),
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: ({ signal }) => tenancyService.getProject(projectId, signal),
    select: (response) => response.data,
    enabled: Boolean(projectId),
  });
}

export function useCreateProject(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; slug: string }) =>
      tenancyService.createProject(workspaceId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['workspaces', workspaceId, 'projects'] }),
  });
}

export function useInviteMember(organizationId: string) {
  return useMutation({
    mutationFn: (payload: { email: string; role: MemberRole }) =>
      tenancyService.inviteMember(organizationId, payload),
  });
}
