/**
 * Activity Log Types
 * Type definitions for activity logging and audit trails
 */

export type ActivityAction =
  | 'create'
  | 'update'
  | 'delete'
  | 'login'
  | 'logout'
  | 'invite'
  | 'accept_invitation'
  | 'decline_invitation'
  | 'change_role'
  | 'enable_2fa'
  | 'disable_2fa'
  | 'update_permissions'
  | 'execute'
  | 'publish'
  | 'unpublish';

export type ActivityResourceType =
  | 'account'
  | 'agent'
  | 'team'
  | 'permission'
  | 'knowledge_base'
  | 'data_source'
  | 'tool'
  | 'widget'
  | 'slack_bot'
  | 'database_connection'
  | 'scheduled_task';

export interface ActivityLog {
  id: string;
  account_id: string;
  account_name?: string;
  account_email?: string;
  action: ActivityAction;
  resource_type: ActivityResourceType;
  resource_id?: string;
  resource_name?: string;
  details?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface ActivityLogFilters {
  account_id?: string;
  action?: ActivityAction;
  resource_type?: ActivityResourceType;
  resource_id?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface ActivityLogStats {
  total_activities: number;
  activities_by_action: Record<ActivityAction, number>;
  activities_by_resource: Record<ActivityResourceType, number>;
  recent_activities: ActivityLog[];
}

// Activity action labels for display
export const ACTIVITY_ACTION_LABELS: Record<ActivityAction, string> = {
  create: 'Created',
  update: 'Updated',
  delete: 'Deleted',
  login: 'Logged in',
  logout: 'Logged out',
  invite: 'Invited',
  accept_invitation: 'Accepted invitation',
  decline_invitation: 'Declined invitation',
  change_role: 'Changed role',
  enable_2fa: 'Enabled 2FA',
  disable_2fa: 'Disabled 2FA',
  update_permissions: 'Updated permissions',
  execute: 'Executed',
  publish: 'Published',
  unpublish: 'Unpublished',
};

// Resource type labels for display
export const RESOURCE_TYPE_LABELS: Record<ActivityResourceType, string> = {
  account: 'Account',
  agent: 'Agent',
  team: 'Team',
  permission: 'Permission',
  knowledge_base: 'Knowledge Base',
  data_source: 'Data Source',
  tool: 'Tool',
  widget: 'Widget',
  slack_bot: 'Slack Bot',
  database_connection: 'Database Connection',
  scheduled_task: 'Scheduled Task',
};

// Activity action colors for UI
export const ACTIVITY_ACTION_COLORS: Record<ActivityAction, string> = {
  create: 'green',
  update: 'blue',
  delete: 'red',
  login: 'purple',
  logout: 'gray',
  invite: 'blue',
  accept_invitation: 'green',
  decline_invitation: 'orange',
  change_role: 'blue',
  enable_2fa: 'green',
  disable_2fa: 'orange',
  update_permissions: 'blue',
  execute: 'purple',
  publish: 'green',
  unpublish: 'orange',
};

// Helper function to format activity description
export const formatActivityDescription = (log: ActivityLog): string => {
  const action = ACTIVITY_ACTION_LABELS[log.action] || log.action;
  const resourceType = RESOURCE_TYPE_LABELS[log.resource_type] || log.resource_type;
  const resourceName = log.resource_name || log.resource_id || 'unknown';
  
  return `${action} ${resourceType.toLowerCase()}: ${resourceName}`;
};
