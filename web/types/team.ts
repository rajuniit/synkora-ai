/**
 * Team and Invitation Types
 * Type definitions for team members and invitations
 */

export type UserRole = 'owner' | 'admin' | 'editor' | 'member';

export interface TeamMember {
  account_id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: UserRole;
  invited_by?: string;
  invited_by_name?: string;
  joined_at: string;
  custom_permissions?: string[];
  last_login_at?: string;
}

export interface TeamInvitation {
  id: string;
  email: string;
  role: UserRole;
  invited_by: string;
  invited_by_name?: string;
  status: InvitationStatus;
  token: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
}

export type InvitationStatus = 'pending' | 'accepted' | 'declined' | 'expired';

export interface InviteMemberRequest {
  email: string;
  role: UserRole;
  custom_permissions?: string[];
}

export interface UpdateMemberRoleRequest {
  role: UserRole;
}

export interface UpdateMemberPermissionsRequest {
  custom_permissions: string[];
}

export interface AcceptInvitationRequest {
  token: string;
}

export interface DeclineInvitationRequest {
  token: string;
}

export interface TeamMemberFilters {
  role?: UserRole;
  search?: string;
}

export interface InvitationFilters {
  status?: InvitationStatus;
  search?: string;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  owner: 'Owner',
  admin: 'Admin',
  editor: 'Editor',
  member: 'Member',
};

export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  owner: 'Full access to all features and settings',
  admin: 'Manage team members and most settings',
  editor: 'Create and edit content',
  member: 'View and interact with content',
};

export const ROLE_COLORS: Record<UserRole, string> = {
  owner: 'purple',
  admin: 'blue',
  editor: 'green',
  member: 'gray',
};
