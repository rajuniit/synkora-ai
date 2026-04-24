/**
 * Team Management Hooks
 * Custom hooks for team-related API operations
 */

import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api/client';
import { extractErrorMessage } from '@/lib/api/error';
import type {
  TeamMember,
  TeamInvitation,
  InviteMemberRequest,
  UpdateMemberRoleRequest,
} from '@/types/team';

const getErrorMessage = (err: any, fallback: string): string => extractErrorMessage(err, fallback);

export function useTeam() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const clearMessages = useCallback(() => {
    setError(null);
    setSuccess(null);
  }, []);

  const getTeamMembers = useCallback(async (tenantId: string): Promise<TeamMember[]> => {
    setLoading(true);
    try {
      const response = await apiClient.request('GET', `/api/v1/teams/members`);
      return response.data || response;
    } catch (err: any) {
      setError(getErrorMessage(err, 'Failed to fetch team members'));
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const inviteTeamMember = useCallback(
    async (tenantId: string, data: InviteMemberRequest): Promise<TeamInvitation | null> => {
      setLoading(true);
      clearMessages();
      try {
        const response = await apiClient.request('POST', `/api/v1/teams/invitations`, data);
        setSuccess(`Invitation sent successfully to ${data.email}`);
        return response.data || response;
      } catch (err: any) {
        setError(getErrorMessage(err, 'Failed to invite team member'));
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const updateTeamMember = useCallback(
    async (tenantId: string, memberId: string, data: UpdateMemberRoleRequest): Promise<TeamMember | null> => {
      setLoading(true);
      clearMessages();
      try {
        const response = await apiClient.request('PUT', `/api/v1/teams/members/${memberId}`, data);
        setSuccess('Team member updated successfully');
        return response.data || response;
      } catch (err: any) {
        setError(getErrorMessage(err, 'Failed to update team member'));
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const removeTeamMember = useCallback(
    async (tenantId: string, memberId: string): Promise<boolean> => {
      setLoading(true);
      clearMessages();
      try {
        await apiClient.request('DELETE', `/api/v1/teams/members/${memberId}`);
        setSuccess('Team member removed successfully');
        return true;
      } catch (err: any) {
        setError(getErrorMessage(err, 'Failed to remove team member'));
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const getPendingInvitations = useCallback(async (tenantId: string): Promise<TeamInvitation[]> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.request('GET', `/api/v1/teams/invitations`);
      return response.data || response || [];
    } catch (err: any) {
      // Don't show error for empty invitations
      console.error('Failed to fetch invitations:', err);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const resendInvitation = useCallback(
    async (tenantId: string, invitationId: string): Promise<boolean> => {
      setLoading(true);
      clearMessages();
      try {
        await apiClient.request('POST', `/api/v1/teams/invitations/${invitationId}/resend`);
        setSuccess('Invitation resent successfully');
        return true;
      } catch (err: any) {
        setError(getErrorMessage(err, 'Failed to resend invitation'));
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const cancelInvitation = useCallback(
    async (tenantId: string, invitationId: string): Promise<boolean> => {
      setLoading(true);
      clearMessages();
      try {
        await apiClient.request('DELETE', `/api/v1/teams/invitations/${invitationId}`);
        setSuccess('Invitation cancelled successfully');
        return true;
      } catch (err: any) {
        setError(getErrorMessage(err, 'Failed to cancel invitation'));
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const acceptInvitation = useCallback(async (token: string): Promise<boolean> => {
    setLoading(true);
    clearMessages();
    try {
      await apiClient.request('POST', `/api/v1/teams/invitations/accept`, { token });
      setSuccess('Invitation accepted successfully');
      return true;
    } catch (err: any) {
      setError(getErrorMessage(err, 'Failed to accept invitation'));
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const getDomainSettings = useCallback(async (): Promise<{ domain: string | null; auto_assign_domain_users: boolean } | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.request('GET', `/api/v1/teams/settings/domain`);
      return response.data || response;
    } catch (err: any) {
      setError(getErrorMessage(err, 'Failed to fetch domain settings'));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateDomainSettings = useCallback(
    async (data: { domain: string | null; auto_assign_domain_users: boolean }): Promise<boolean> => {
      setLoading(true);
      clearMessages();
      try {
        await apiClient.request('PUT', `/api/v1/teams/settings/domain`, data);
        setSuccess('Domain settings updated successfully');
        return true;
      } catch (err: any) {
        setError(getErrorMessage(err, 'Failed to update domain settings'));
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return {
    loading,
    error,
    success,
    clearMessages,
    getTeamMembers,
    inviteTeamMember,
    updateTeamMember,
    removeTeamMember,
    getPendingInvitations,
    resendInvitation,
    cancelInvitation,
    acceptInvitation,
    getDomainSettings,
    updateDomainSettings,
  };
}
