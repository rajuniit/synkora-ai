'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  SocialProvider,
  SocialAuthProvider,
  LinkProviderRequest,
  ProviderStatus,
} from '@/types/social-auth';
import {
  getLoginUrl,
  getLinkedProviders,
  linkProvider,
  unlinkProvider,
  getProviderStatus,
} from '@/lib/api/social-auth';

interface UseSocialAuthReturn {
  // State
  linkedProviders: SocialAuthProvider[];
  loading: boolean;
  error: string | null;
  
  // Actions
  initiateLogin: (provider: SocialProvider, redirectUrl?: string) => Promise<void>;
  fetchLinkedProviders: () => Promise<void>;
  linkSocialProvider: (data: LinkProviderRequest) => Promise<void>;
  unlinkSocialProvider: (provider: SocialProvider) => Promise<void>;
  checkProviderStatus: (provider: SocialProvider) => Promise<ProviderStatus>;
  clearError: () => void;
}

export function useSocialAuth(): UseSocialAuthReturn {
  const router = useRouter();
  const [linkedProviders, setLinkedProviders] = useState<SocialAuthProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const initiateLogin = useCallback(async (
    provider: SocialProvider,
    redirectUrl?: string
  ) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await getLoginUrl(provider, redirectUrl);
      
      // Redirect to OAuth provider
      window.location.href = response.authorization_url;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to initiate login';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchLinkedProviders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const providers = await getLinkedProviders();
      setLinkedProviders(providers);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch linked providers';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const linkSocialProvider = useCallback(async (data: LinkProviderRequest) => {
    try {
      setLoading(true);
      setError(null);
      
      await linkProvider(data);
      
      // Refresh linked providers list
      await fetchLinkedProviders();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to link provider';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchLinkedProviders]);

  const unlinkSocialProvider = useCallback(async (provider: SocialProvider) => {
    try {
      setLoading(true);
      setError(null);
      
      await unlinkProvider(provider);
      
      // Refresh linked providers list
      await fetchLinkedProviders();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to unlink provider';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchLinkedProviders]);

  const checkProviderStatus = useCallback(async (
    provider: SocialProvider
  ): Promise<ProviderStatus> => {
    try {
      setLoading(true);
      setError(null);
      
      return await getProviderStatus(provider);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to check provider status';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    linkedProviders,
    loading,
    error,
    initiateLogin,
    fetchLinkedProviders,
    linkSocialProvider,
    unlinkSocialProvider,
    checkProviderStatus,
    clearError,
  };
}
