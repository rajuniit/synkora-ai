/**
 * Profile Management Hooks
 * Custom hooks for profile-related API operations
 */

import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '@/lib/api/client';
import type {
  Profile,
  UpdateProfileRequest,
  UpdatePasswordRequest,
  Enable2FAResponse,
  Verify2FARequest,
  NotificationPreferences,
} from '@/types/profile';

export function useProfile() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getProfile = useCallback(async (): Promise<Profile | null> => {
    setLoading(true);
    setError(null);
    try {
      // Call /profile/me endpoint which returns the profile data directly
      const response = await apiClient.request('GET', '/api/v1/profile/me');
      
      // The response should be the profile data directly
      const profileData = response.data || response;
      
      if (profileData) {
        const profile: Profile = {
          id: profileData.id,
          email: profileData.email,
          name: profileData.name,
          avatar_url: profileData.avatar_url || undefined,
          phone: profileData.phone || undefined,
          bio: profileData.bio || undefined,
          company: profileData.company || undefined,
          job_title: profileData.job_title || undefined,
          location: profileData.location || undefined,
          website: profileData.website || undefined,
          two_factor_enabled: profileData.two_factor_enabled || false,
          two_factor_secret: profileData.two_factor_secret || undefined,
          last_login_at: profileData.last_login_at || undefined,
          last_login_ip: profileData.last_login_ip || undefined,
          is_platform_admin: profileData.is_platform_admin || false,
          notification_preferences: profileData.notification_preferences || {
            email_notifications: true,
            team_invitations: true,
            security_alerts: true,
            product_updates: false,
            marketing_emails: false,
          },
          created_at: profileData.created_at,
          updated_at: profileData.updated_at || profileData.created_at,
        };
        setProfile(profile);
        return profile;
      }
      
      return null;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch profile');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Load profile on mount
  useEffect(() => {
    getProfile();
  }, [getProfile]);

  const updateProfile = useCallback(async (data: UpdateProfileRequest): Promise<Profile | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.request('PUT', '/api/v1/profile/me', data);
      const updatedProfile = response.data || response;
      setProfile(updatedProfile);
      return updatedProfile;
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadAvatar = useCallback(async (file: File): Promise<string> => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await apiClient.request('POST', '/api/v1/profile/me/avatar', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      const avatarUrl = response.data?.avatar_url || response.avatar_url;
      
      // Update local profile state
      if (profile && avatarUrl) {
        setProfile({ ...profile, avatar_url: avatarUrl });
      }
      
      return avatarUrl;
    } catch (err: any) {
      setError(err.message || 'Failed to upload avatar');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [profile]);

  const updatePassword = useCallback(async (data: UpdatePasswordRequest): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.request('POST', '/api/v1/profile/me/password', data);
      return true;
    } catch (err: any) {
      setError(err.message || 'Failed to update password');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateNotificationPreferences = useCallback(
    async (preferences: NotificationPreferences): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await apiClient.request('PUT', '/api/v1/profile/me/notifications', preferences);
        return true;
      } catch (err: any) {
        setError(err.message || 'Failed to update notification preferences');
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const enable2FA = useCallback(async (): Promise<Enable2FAResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.request('POST', '/api/v1/profile/me/2fa/enable');
      return response.data || response;
    } catch (err: any) {
      setError(err.message || 'Failed to enable 2FA');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const verify2FA = useCallback(async (data: Verify2FARequest): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.request('POST', '/api/v1/profile/me/2fa/verify', data);
      return true;
    } catch (err: any) {
      setError(err.message || 'Failed to verify 2FA code');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const disable2FA = useCallback(async (): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.request('POST', '/api/v1/profile/me/2fa/disable');
      return true;
    } catch (err: any) {
      setError(err.message || 'Failed to disable 2FA');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteAccount = useCallback(async (password: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.request('POST', '/api/v1/profile/me/delete', { password });
      return true;
    } catch (err: any) {
      setError(err.message || 'Failed to delete account');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    profile,
    loading,
    error,
    getProfile,
    updateProfile,
    uploadAvatar,
    updatePassword,
    updateNotificationPreferences,
    enable2FA,
    verify2FA,
    disable2FA,
    deleteAccount,
  };
}
