'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getSubscriptionPlans,
  getCurrentSubscription,
  createSubscription,
  upgradeSubscription,
  cancelSubscription,
  reactivateSubscription,
  getCreditBalance,
  getCreditTransactions,
  createCreditTopup,
  getCreditTopups,
  getUsageSummary,
  getUsageTrends,
  getAgentUsageBreakdown,
  getActionUsageBreakdown,
  getPeakUsageTimes,
  getAgentPricing,
  setAgentPricing,
  getAgentRevenue,
  getAgentEarnings,
  getCreatorRevenue,
  getCreatorEarnings,
  getPaymentMethods,
  addPaymentMethod,
  removePaymentMethod,
  setDefaultPaymentMethod,
  getInvoices,
  downloadInvoice,
  createBillingPortalSession,
  exportUsageReport,
} from '@/lib/api/billing';
import type {
  SubscriptionPlan,
  TenantSubscription,
  CreditBalance,
  CreditTransaction,
  CreditTopup,
  AgentPricing,
  AgentRevenue,
  CreateSubscriptionRequest,
  UpgradeSubscriptionRequest,
  TopupCreditsRequest,
  SetAgentPricingRequest,
  TransactionFilters,
  UsageFilters,
  UsageSummary,
  UsageTrend,
  AgentUsageBreakdown,
  ActionUsageBreakdown,
  PeakUsageTime,
} from '@/types/billing';

export function useBilling() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: any) => {
    const message = err?.message || 'An error occurred';
    setError(message);
    console.error('Billing error:', err);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    loading,
    error,
    clearError,
    setLoading,
    handleError,
  };
}

export function useSubscriptionPlans() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const { loading, error, setLoading, handleError } = useBilling();

  const fetchPlans = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getSubscriptionPlans();
      setPlans(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  return { plans, loading, error, refetch: fetchPlans };
}

export function useSubscription() {
  const [subscription, setSubscription] = useState<TenantSubscription | null>(null);
  const { loading, error, setLoading, handleError, clearError } = useBilling();

  const fetchSubscription = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCurrentSubscription();
      setSubscription(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  const create = useCallback(async (data: CreateSubscriptionRequest) => {
    try {
      clearError();
      setLoading(true);
      const result = await createSubscription(data);
      setSubscription(result);
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError, clearError]);

  const upgrade = useCallback(async (data: UpgradeSubscriptionRequest) => {
    try {
      clearError();
      setLoading(true);
      const result = await upgradeSubscription(data);
      setSubscription(result);
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError, clearError]);

  const cancel = useCallback(async (immediate: boolean = false) => {
    try {
      clearError();
      setLoading(true);
      await cancelSubscription(immediate);
      await fetchSubscription();
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError, clearError, fetchSubscription]);

  const reactivate = useCallback(async () => {
    try {
      clearError();
      setLoading(true);
      const result = await reactivateSubscription();
      setSubscription(result);
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError, clearError]);

  useEffect(() => {
    fetchSubscription();
  }, [fetchSubscription]);

  return {
    subscription,
    loading,
    error,
    create,
    upgrade,
    cancel,
    reactivate,
    refetch: fetchSubscription,
  };
}

export function useCredits() {
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [topups, setTopups] = useState<CreditTopup[]>([]);
  const { loading, error, setLoading, handleError, clearError } = useBilling();

  const fetchBalance = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCreditBalance();
      setBalance(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  const fetchTransactions = useCallback(async (filters?: TransactionFilters) => {
    try {
      setLoading(true);
      const data = await getCreditTransactions(filters);
      setTransactions(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  const fetchTopups = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCreditTopups();
      setTopups(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  const topup = useCallback(async (data: TopupCreditsRequest) => {
    try {
      clearError();
      setLoading(true);
      const result = await createCreditTopup(data);
      await fetchBalance();
      await fetchTopups();
      return result;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError, clearError, fetchBalance, fetchTopups]);

  useEffect(() => {
    fetchBalance();
  }, [fetchBalance]);

  return {
    balance,
    transactions,
    topups,
    loading,
    error,
    topup,
    refetchBalance: fetchBalance,
    refetchTransactions: fetchTransactions,
    refetchTopups: fetchTopups,
  };
}

export function useUsageAnalytics(filters?: UsageFilters) {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [trends, setTrends] = useState<UsageTrend[]>([]);
  const [agentBreakdown, setAgentBreakdown] = useState<AgentUsageBreakdown[]>([]);
  const [actionBreakdown, setActionBreakdown] = useState<ActionUsageBreakdown[]>([]);
  const [peakTimes, setPeakTimes] = useState<PeakUsageTime[]>([]);
  const { loading, error, setLoading, handleError } = useBilling();

  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryData, trendsData, agentData, actionData, peakData] = await Promise.all([
        getUsageSummary(filters),
        getUsageTrends(filters),
        getAgentUsageBreakdown(filters),
        getActionUsageBreakdown(filters),
        getPeakUsageTimes(filters),
      ]);
      setSummary(summaryData);
      setTrends(trendsData);
      setAgentBreakdown(agentData);
      setActionBreakdown(actionData);
      setPeakTimes(peakData);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [filters, setLoading, handleError]);

  const exportReport = useCallback(async (format: 'csv' | 'pdf' = 'csv') => {
    try {
      setLoading(true);
      const blob = await exportUsageReport(filters, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `usage-report-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [filters, setLoading, handleError]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return {
    summary,
    trends,
    agentBreakdown,
    actionBreakdown,
    peakTimes,
    loading,
    error,
    refetch: fetchAnalytics,
    exportReport,
  };
}

export function useAgentPricing(agentId: string) {
  const [pricing, setPricing] = useState<AgentPricing | null>(null);
  const [revenue, setRevenue] = useState<AgentRevenue[]>([]);
  const [earnings, setEarnings] = useState<any>(null);
  const { loading, error, setLoading, handleError, clearError } = useBilling();

  const fetchPricing = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getAgentPricing(agentId);
      setPricing(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [agentId, setLoading, handleError]);

  const fetchRevenue = useCallback(async (filters?: { start_date?: string; end_date?: string }) => {
    try {
      setLoading(true);
      const data = await getAgentRevenue(agentId, filters);
      setRevenue(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [agentId, setLoading, handleError]);

  const fetchEarnings = useCallback(async (period: 'daily' | 'weekly' | 'monthly' | 'yearly' = 'monthly') => {
    try {
      setLoading(true);
      const data = await getAgentEarnings(agentId, period);
      setEarnings(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [agentId, setLoading, handleError]);

  const updatePricing = useCallback(async (data: Partial<AgentPricing>) => {
    try {
      clearError();
      setLoading(true);
      const result = await setAgentPricing(agentId, data as SetAgentPricingRequest);
      setPricing(result);
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [agentId, setLoading, handleError, clearError]);

  useEffect(() => {
    if (agentId) {
      fetchPricing();
      fetchRevenue();
      fetchEarnings();
    }
  }, [agentId, fetchPricing, fetchRevenue, fetchEarnings]);

  return {
    pricing,
    revenue,
    earnings,
    loading,
    error,
    updatePricing,
    refetchPricing: fetchPricing,
    refetchRevenue: fetchRevenue,
    refetchEarnings: fetchEarnings,
  };
}

export function useCreatorRevenue() {
  const [revenue, setRevenue] = useState<AgentRevenue[]>([]);
  const [earnings, setEarnings] = useState<any>(null);
  const { loading, error, setLoading, handleError } = useBilling();

  const fetchRevenue = useCallback(async (filters?: { start_date?: string; end_date?: string }) => {
    try {
      setLoading(true);
      const data = await getCreatorRevenue(filters);
      setRevenue(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  const fetchEarnings = useCallback(async (period: 'daily' | 'weekly' | 'monthly' | 'yearly' = 'monthly') => {
    try {
      setLoading(true);
      const data = await getCreatorEarnings(period);
      setEarnings(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  useEffect(() => {
    fetchRevenue();
    fetchEarnings();
  }, [fetchRevenue, fetchEarnings]);

  return {
    revenue,
    earnings,
    loading,
    error,
    refetchRevenue: fetchRevenue,
    refetchEarnings: fetchEarnings,
  };
}

export function usePaymentMethods() {
  const [paymentMethods, setPaymentMethods] = useState<any[]>([]);
  const { loading, error, setLoading, handleError, clearError } = useBilling();

  const fetchPaymentMethods = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getPaymentMethods();
      setPaymentMethods(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  const add = useCallback(async (paymentMethodId: string) => {
    try {
      clearError();
      setLoading(true);
      await addPaymentMethod(paymentMethodId);
      await fetchPaymentMethods();
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError, clearError, fetchPaymentMethods]);

  const remove = useCallback(async (paymentMethodId: string) => {
    try {
      clearError();
      setLoading(true);
      await removePaymentMethod(paymentMethodId);
      await fetchPaymentMethods();
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError, clearError, fetchPaymentMethods]);

  const setDefault = useCallback(async (paymentMethodId: string) => {
    try {
      clearError();
      setLoading(true);
      await setDefaultPaymentMethod(paymentMethodId);
      await fetchPaymentMethods();
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError, clearError, fetchPaymentMethods]);

  useEffect(() => {
    fetchPaymentMethods();
  }, [fetchPaymentMethods]);

  return {
    paymentMethods,
    loading,
    error,
    add,
    remove,
    setDefault,
    refetch: fetchPaymentMethods,
  };
}

export function useInvoices() {
  const [invoices, setInvoices] = useState<any[]>([]);
  const { loading, error, setLoading, handleError } = useBilling();

  const fetchInvoices = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getInvoices();
      setInvoices(data);
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  const download = useCallback(async (invoiceId: string) => {
    try {
      setLoading(true);
      const blob = await downloadInvoice(invoiceId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice-${invoiceId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  return {
    invoices,
    loading,
    error,
    download,
    refetch: fetchInvoices,
  };
}

export function useBillingPortal() {
  const { loading, error, setLoading, handleError } = useBilling();

  const openPortal = useCallback(async () => {
    try {
      setLoading(true);
      const { url } = await createBillingPortalSession();
      window.location.href = url;
    } catch (err) {
      handleError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [setLoading, handleError]);

  return {
    loading,
    error,
    openPortal,
  };
}
