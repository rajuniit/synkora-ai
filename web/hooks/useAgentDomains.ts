/**
 * React Hook for Agent Domains Management
 * 
 * Provides state management and operations for agent custom domains.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  listAgentDomains,
  getAgentDomain,
  createAgentDomain,
  updateAgentDomain,
  deleteAgentDomain,
  getDNSRecords,
  verifyDomainDNS,
} from '@/lib/api/agent-domains';
import type {
  AgentDomain,
  AgentDomainCreate,
  AgentDomainUpdate,
  DNSRecordsResponse,
  DNSVerificationResponse,
} from '@/types/agent-domain';

interface UseAgentDomainsOptions {
  agentId?: string;
  autoFetch?: boolean;
}

interface UseAgentDomainsReturn {
  domains: AgentDomain[];
  loading: boolean;
  error: string | null;
  fetchDomains: () => Promise<void>;
  getDomain: (domainId: string) => Promise<AgentDomain | null>;
  createDomain: (data: AgentDomainCreate) => Promise<AgentDomain | null>;
  updateDomain: (domainId: string, data: AgentDomainUpdate) => Promise<AgentDomain | null>;
  deleteDomain: (domainId: string) => Promise<boolean>;
  getDNSRecordsForDomain: (domainId: string) => Promise<DNSRecordsResponse | null>;
  verifyDomain: (domainId: string) => Promise<DNSVerificationResponse | null>;
  refreshDomain: (domainId: string) => Promise<void>;
}

export function useAgentDomains(options: UseAgentDomainsOptions = {}): UseAgentDomainsReturn {
  const { agentId, autoFetch = true } = options;
  
  const [domains, setDomains] = useState<AgentDomain[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch all domains for the agent
   */
  const fetchDomains = useCallback(async () => {
    if (!agentId) {
      setError('Agent ID is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await listAgentDomains(agentId);
      setDomains(data);
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch domains';
      setError(errorMessage);
      console.error('Error fetching domains:', err);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  /**
   * Get a specific domain
   */
  const getDomain = useCallback(async (domainId: string): Promise<AgentDomain | null> => {
    if (!agentId) {
      setError('Agent ID is required');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await getAgentDomain(agentId, domainId);
      return data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch domain';
      setError(errorMessage);
      console.error('Error fetching domain:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  /**
   * Create a new domain
   */
  const createDomain = useCallback(async (data: AgentDomainCreate): Promise<AgentDomain | null> => {
    if (!agentId) {
      setError('Agent ID is required');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const newDomain = await createAgentDomain(agentId, data);
      setDomains(prev => [...prev, newDomain]);
      return newDomain;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to create domain';
      setError(errorMessage);
      console.error('Error creating domain:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  /**
   * Update an existing domain
   */
  const updateDomain = useCallback(async (
    domainId: string,
    data: AgentDomainUpdate
  ): Promise<AgentDomain | null> => {
    if (!agentId) {
      setError('Agent ID is required');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const updatedDomain = await updateAgentDomain(agentId, domainId, data);
      setDomains(prev => prev.map(d => d.id === domainId ? updatedDomain : d));
      return updatedDomain;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to update domain';
      setError(errorMessage);
      console.error('Error updating domain:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  /**
   * Delete a domain
   */
  const deleteDomain = useCallback(async (domainId: string): Promise<boolean> => {
    if (!agentId) {
      setError('Agent ID is required');
      return false;
    }

    setLoading(true);
    setError(null);

    try {
      await deleteAgentDomain(agentId, domainId);
      setDomains(prev => prev.filter(d => d.id !== domainId));
      return true;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to delete domain';
      setError(errorMessage);
      console.error('Error deleting domain:', err);
      return false;
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  /**
   * Get DNS records for a domain
   */
  const getDNSRecordsForDomain = useCallback(async (
    domainId: string
  ): Promise<DNSRecordsResponse | null> => {
    if (!agentId) {
      setError('Agent ID is required');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const records = await getDNSRecords(agentId, domainId);
      return records;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch DNS records';
      setError(errorMessage);
      console.error('Error fetching DNS records:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  /**
   * Verify domain DNS configuration
   */
  const verifyDomain = useCallback(async (
    domainId: string
  ): Promise<DNSVerificationResponse | null> => {
    if (!agentId) {
      setError('Agent ID is required');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await verifyDomainDNS(agentId, domainId);
      
      // Update the domain in the list with new verification status
      if (result.is_verified) {
        setDomains(prev => prev.map(d => 
          d.id === domainId 
            ? { ...d, is_verified: true, verified_at: new Date().toISOString() }
            : d
        ));
      }
      
      return result;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to verify domain';
      setError(errorMessage);
      console.error('Error verifying domain:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  /**
   * Refresh a specific domain's data
   */
  const refreshDomain = useCallback(async (domainId: string): Promise<void> => {
    if (!agentId) {
      setError('Agent ID is required');
      return;
    }

    try {
      const updatedDomain = await getAgentDomain(agentId, domainId);
      setDomains(prev => prev.map(d => d.id === domainId ? updatedDomain : d));
    } catch (err: any) {
      console.error('Error refreshing domain:', err);
    }
  }, [agentId]);

  // Auto-fetch domains on mount if enabled
  useEffect(() => {
    if (autoFetch && agentId) {
      fetchDomains();
    }
  }, [autoFetch, agentId, fetchDomains]);

  return {
    domains,
    loading,
    error,
    fetchDomains,
    getDomain,
    createDomain,
    updateDomain,
    deleteDomain,
    getDNSRecordsForDomain,
    verifyDomain,
    refreshDomain,
  };
}

/**
 * Hook for managing a single domain
 */
export function useAgentDomain(agentId: string, domainId: string) {
  const [domain, setDomain] = useState<AgentDomain | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDomain = useCallback(async () => {
    if (!agentId || !domainId) {
      setError('Agent ID and Domain ID are required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await getAgentDomain(agentId, domainId);
      setDomain(data);
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch domain';
      setError(errorMessage);
      console.error('Error fetching domain:', err);
    } finally {
      setLoading(false);
    }
  }, [agentId, domainId]);

  useEffect(() => {
    fetchDomain();
  }, [fetchDomain]);

  return {
    domain,
    loading,
    error,
    refetch: fetchDomain,
  };
}
