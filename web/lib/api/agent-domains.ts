/**
 * Agent Domains API Client
 * 
 * API client functions for agent domain management.
 */

import { apiClient } from './client';
import type {
  AgentDomain,
  AgentDomainCreate,
  AgentDomainUpdate,
  DNSRecordsResponse,
  DNSVerificationResponse,
} from '@/types/agent-domain';

/**
 * List all domains for an agent
 */
export async function listAgentDomains(agentId: string): Promise<AgentDomain[]> {
  const data = await apiClient.request('GET', `/api/v1/agents/${agentId}/domains`);
  return data.data?.domains || data;
}

/**
 * Get a specific domain
 */
export async function getAgentDomain(
  agentId: string,
  domainId: string
): Promise<AgentDomain> {
  const data = await apiClient.request('GET', `/api/v1/agents/${agentId}/domains/${domainId}`);
  return data.data || data;
}

/**
 * Create a new domain for an agent
 */
export async function createAgentDomain(
  agentId: string,
  domainData: AgentDomainCreate
): Promise<AgentDomain> {
  const data = await apiClient.request('POST', `/api/v1/agents/${agentId}/domains`, domainData);
  return data.data || data;
}

/**
 * Update a domain
 */
export async function updateAgentDomain(
  agentId: string,
  domainId: string,
  domainData: AgentDomainUpdate
): Promise<AgentDomain> {
  const data = await apiClient.request('PUT', `/api/v1/agents/${agentId}/domains/${domainId}`, domainData);
  return data.data || data;
}

/**
 * Delete a domain
 */
export async function deleteAgentDomain(
  agentId: string,
  domainId: string
): Promise<void> {
  await apiClient.request('DELETE', `/api/v1/agents/${agentId}/domains/${domainId}`);
}

/**
 * Get required DNS records for a custom domain
 */
export async function getDNSRecords(
  agentId: string,
  domainId: string
): Promise<DNSRecordsResponse> {
  const data = await apiClient.request('GET', `/api/v1/agents/${agentId}/domains/${domainId}/dns-records`);
  return data.data || data;
}

/**
 * Verify DNS configuration for a custom domain
 */
export async function verifyDomainDNS(
  agentId: string,
  domainId: string
): Promise<DNSVerificationResponse> {
  const data = await apiClient.request('POST', `/api/v1/agents/${agentId}/domains/${domainId}/verify`);
  return data.data || data;
}