'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  OktaTenant,
  OktaTenantCreate,
  OktaTenantUpdate,
  OktaSSOConfig,
} from '@/types/okta-sso';
import { oktaSSOApi } from '@/lib/api/okta-sso';

interface UseOktaSSOReturn {
  // State
  tenant: OktaTenant | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchTenant: () => Promise<void>;
  createTenant: (data: OktaTenantCreate) => Promise<OktaTenant>;
  updateTenant: (data: OktaTenantUpdate) => Promise<OktaTenant>;
  deleteTenant: () => Promise<void>;
  testConfig: (config: OktaSSOConfig) => Promise<{ success: boolean; message: string }>;
  initiateLogin: (redirectUrl?: string) => Promise<void>;
  getStatus: () => Promise<{ enabled: boolean; configured: boolean }>;
  clearError: () => void;
}

export function useOktaSSO(): UseOktaSSOReturn {
  const router = useRouter();
  const [tenant, setTenant] = useState<OktaTenant | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const fetchTenant = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await oktaSSOApi.getOktaTenant();
      setTenant(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch Okta configuration';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const createTenant = useCallback(async (
    data: OktaTenantCreate
  ): Promise<OktaTenant> => {
    try {
      setLoading(true);
      setError(null);
      
      const newTenant = await oktaSSOApi.createOktaTenant(data);
      setTenant(newTenant);
      
      return newTenant;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create Okta tenant';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateTenant = useCallback(async (
    data: OktaTenantUpdate
  ): Promise<OktaTenant> => {
    try {
      setLoading(true);
      setError(null);
      
      const updatedTenant = await oktaSSOApi.updateOktaTenant(data);
      setTenant(updatedTenant);
      
      return updatedTenant;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update Okta tenant';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteTenant = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      await oktaSSOApi.deleteOktaTenant();
      setTenant(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete Okta tenant';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const testConfig = useCallback(async (
    config: OktaSSOConfig
  ): Promise<{ success: boolean; message: string }> => {
    try {
      setLoading(true);
      setError(null);
      
      return await oktaSSOApi.testOktaConfig(config);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to test Okta configuration';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const initiateLogin = useCallback(async (redirectUrl?: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await oktaSSOApi.getOktaLoginUrl(redirectUrl);
      
      // Redirect to Okta login
      window.location.href = response.url;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to initiate Okta login';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      return await oktaSSOApi.getOktaStatus();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to get Okta status';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    tenant,
    loading,
    error,
    fetchTenant,
    createTenant,
    updateTenant,
    deleteTenant,
    testConfig,
    initiateLogin,
    getStatus,
    clearError,
  };
}
