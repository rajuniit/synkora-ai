/**
 * Permissions Management Hooks
 * Custom hooks for permissions-related API operations
 */

import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';
import type {
  Permission,
  RolePermissionsResponse,
  CheckPermissionRequest,
  CheckPermissionResponse,
} from '@/types/permissions';

export function usePermissions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userPermissions, setUserPermissions] = useState<string[]>([]);

  const getAllPermissions = useCallback(async (): Promise<Permission[]> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.request('GET', '/api/v1/permissions');
      return response.data || response;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch permissions');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const getRolePermissions = useCallback(async (tenantId: string, role: string): Promise<RolePermissionsResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.request('GET', `/api/v1/tenants/${tenantId}/permissions/roles/${role}`);
      return response.data || response;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch role permissions');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateRolePermissions = useCallback(
    async (tenantId: string, role: string, permissionIds: string[]): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await apiClient.request('PUT', `/api/v1/tenants/${tenantId}/permissions/roles/${role}`, {
          permission_ids: permissionIds,
        });
        return true;
      } catch (err: any) {
        setError(err.message || 'Failed to update role permissions');
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const getUserPermissions = useCallback(
    async (tenantId: string, accountId: string): Promise<string[]> => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.request('GET', `/api/v1/tenants/${tenantId}/permissions/users/${accountId}`);
        return response.data?.permissions || response.permissions || [];
      } catch (err: any) {
        setError(err.message || 'Failed to fetch user permissions');
        return [];
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const updateUserPermissions = useCallback(
    async (tenantId: string, accountId: string, permissionIds: string[]): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await apiClient.request('PUT', `/api/v1/tenants/${tenantId}/permissions/users/${accountId}`, {
          permission_ids: permissionIds,
        });
        return true;
      } catch (err: any) {
        setError(err.message || 'Failed to update user permissions');
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const checkPermission = useCallback(
    async (data: CheckPermissionRequest): Promise<CheckPermissionResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const response = await apiClient.request('POST', '/api/v1/permissions/check', data);
        return response.data || response;
      } catch (err: any) {
        setError(err.message || 'Failed to check permission');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Load current user's permissions on mount
  useEffect(() => {
    const loadUserPermissions = async () => {
      try {
        const response = await apiClient.request('GET', '/api/v1/permissions/me');
        // Backend returns permissions in 'effective_permissions' field
        const permissions = response.data?.effective_permissions || response.effective_permissions || 
                          response.data?.permissions || response.permissions || [];
        setUserPermissions(permissions);
      } catch (err) {
        console.error('Failed to load user permissions:', err);
      }
    };
    loadUserPermissions();
  }, []);

  // Helper function to check if user has a specific permission
  const hasPermission = useCallback(
    (resource: string, action: string): boolean => {
      const permissionKey = `${resource}.${action}`;
      return userPermissions.includes(permissionKey);
    },
    [userPermissions]
  );

  return {
    loading,
    error,
    getAllPermissions,
    getRolePermissions,
    updateRolePermissions,
    getUserPermissions,
    updateUserPermissions,
    checkPermission,
    hasPermission,
  };
}
