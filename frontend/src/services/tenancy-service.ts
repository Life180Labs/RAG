import { apiGet, apiPatch, apiPost } from '@/services/api-client';
import type { ApiSuccessResponse } from '@/types/api';
import type { Invitation, MemberRole, Organization, Project, Workspace } from '@/types/tenancy';

// --- Organizations ---

export const listOrganizations = (signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Organization[]>>('/organizations', signal);

export const getOrganization = (organizationId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Organization>>(`/organizations/${organizationId}`, signal);

export const createOrganization = (payload: { name: string; slug: string }) =>
  apiPost<ApiSuccessResponse<Organization>>('/organizations', payload);

export const updateOrganization = (organizationId: string, payload: { name: string }) =>
  apiPatch<ApiSuccessResponse<Organization>>(`/organizations/${organizationId}`, payload);

export const archiveOrganization = (organizationId: string) =>
  apiPost<ApiSuccessResponse<Organization>>(`/organizations/${organizationId}/archive`);

export const restoreOrganization = (organizationId: string) =>
  apiPost<ApiSuccessResponse<Organization>>(`/organizations/${organizationId}/restore`);

// --- Workspaces ---

export const listWorkspaces = (organizationId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Workspace[]>>(`/organizations/${organizationId}/workspaces`, signal);

export const getWorkspace = (workspaceId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Workspace>>(`/workspaces/${workspaceId}`, signal);

export const createWorkspace = (organizationId: string, payload: { name: string; slug: string }) =>
  apiPost<ApiSuccessResponse<Workspace>>(`/organizations/${organizationId}/workspaces`, payload);

export const updateWorkspace = (workspaceId: string, payload: { name: string }) =>
  apiPatch<ApiSuccessResponse<Workspace>>(`/workspaces/${workspaceId}`, payload);

// --- Projects ---

export const listProjects = (workspaceId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Project[]>>(`/workspaces/${workspaceId}/projects`, signal);

export const getProject = (projectId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Project>>(`/projects/${projectId}`, signal);

export const createProject = (workspaceId: string, payload: { name: string; slug: string }) =>
  apiPost<ApiSuccessResponse<Project>>(`/workspaces/${workspaceId}/projects`, payload);

export const updateProject = (projectId: string, payload: { name: string }) =>
  apiPatch<ApiSuccessResponse<Project>>(`/projects/${projectId}`, payload);

// --- Invitations ---

export const inviteMember = (
  organizationId: string,
  payload: { email: string; role: MemberRole },
) =>
  apiPost<ApiSuccessResponse<{ invitation: Invitation; invite_token?: string }>>(
    `/organizations/${organizationId}/invitations`,
    payload,
  );

export const listInvitations = (organizationId: string, signal?: AbortSignal) =>
  apiGet<ApiSuccessResponse<Invitation[]>>(`/organizations/${organizationId}/invitations`, signal);

export const acceptInvitation = (token: string) =>
  apiPost<ApiSuccessResponse<{ accepted: boolean }>>('/invitations/accept', { token });
