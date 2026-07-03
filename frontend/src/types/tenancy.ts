export type ResourceStatus = 'active' | 'archived';
export type MemberRole = 'owner' | 'admin' | 'developer' | 'viewer';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  status: ResourceStatus;
  created_at: string;
  updated_at: string;
}

export interface Workspace {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  status: ResourceStatus;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  status: ResourceStatus;
  owner_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Invitation {
  id: string;
  organization_id: string;
  email: string;
  role: MemberRole;
  status: 'pending' | 'accepted' | 'rejected' | 'expired';
  expires_at: string;
  created_at: string;
}
