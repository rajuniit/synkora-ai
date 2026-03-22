/**
 * Permissions Types
 * Type definitions for permissions and role-permission mappings
 */

export interface Permission {
  id: string;
  name: string;
  description?: string;
  resource: string;
  action: string;
  is_platform_wide: boolean;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface RolePermission {
  id: string;
  role: string;
  permission_id: string;
  permission_name: string;
  tenant_id?: string;
  created_at: string;
}

export interface CreatePermissionRequest {
  name: string;
  description?: string;
  resource: string;
  action: string;
  is_platform_wide?: boolean;
  metadata?: Record<string, any>;
}

export interface UpdatePermissionRequest {
  name?: string;
  description?: string;
  metadata?: Record<string, any>;
}

export interface AssignPermissionToRoleRequest {
  role: string;
}

export interface CheckPermissionRequest {
  permission: string;
}

export interface CheckPermissionResponse {
  has_permission: boolean;
  source?: 'role' | 'custom';
}

export interface RolePermissionsResponse {
  role: string;
  permissions: Permission[];
  tenant_id?: string;
}

export interface PermissionFilters {
  resource?: string;
  action?: string;
  is_platform_wide?: boolean;
  search?: string;
}

// Permission format: {resource}.{action}
// Examples: "agents.create", "team.invite", "settings.manage"
export type PermissionString = string;

// Common permission resources
export const PERMISSION_RESOURCES = {
  AGENTS: 'agents',
  TEAM: 'team',
  SETTINGS: 'settings',
  KNOWLEDGE_BASES: 'knowledge_bases',
  DATA_SOURCES: 'data_sources',
  TOOLS: 'tools',
  WIDGETS: 'widgets',
  SLACK_BOTS: 'slack_bots',
} as const;

// Common permission actions
export const PERMISSION_ACTIONS = {
  CREATE: 'create',
  READ: 'read',
  UPDATE: 'update',
  DELETE: 'delete',
  MANAGE: 'manage',
  INVITE: 'invite',
  EXECUTE: 'execute',
} as const;

// Helper function to format permission string
export const formatPermission = (resource: string, action: string): PermissionString => {
  return `${resource}.${action}`;
};

// Helper function to parse permission string
export const parsePermission = (permission: PermissionString): { resource: string; action: string } => {
  const [resource, action] = permission.split('.');
  return { resource, action };
};
