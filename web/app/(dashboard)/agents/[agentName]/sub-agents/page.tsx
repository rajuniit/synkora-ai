"use client";

import { useParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Plus, Trash2, ArrowUp, ArrowDown, ArrowLeft, Users, Check, X, Workflow, Settings, Save } from "lucide-react";
import { apiClient } from "@/lib/api/client";

interface SubAgent {
  id: string;
  sub_agent_id: string;
  sub_agent_name: string;
  sub_agent_description: string | null;
  execution_order: number;
  is_active: boolean;
  config: Record<string, any> | null;
}

interface AvailableAgent {
  id: string;
  agent_name: string;
  description: string | null;
  agent_type: string;
  status: string;
}

export default function SubAgentsPage() {
  const params = useParams();
  const router = useRouter();
  const agentName = params?.agentName as string;

  const [agent, setAgent] = useState<any>(null);
  const [subAgents, setSubAgents] = useState<SubAgent[]>([]);
  const [availableAgents, setAvailableAgents] = useState<AvailableAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [executionOrder, setExecutionOrder] = useState<number>(0);
  
  // Workflow configuration state
  const [workflowType, setWorkflowType] = useState<string>("");
  const [workflowConfig, setWorkflowConfig] = useState({
    max_iterations: 10,
    timeout_seconds: 300,
    continue_on_error: false,
    aggregate_outputs: true,
  });
  const [customConfigText, setCustomConfigText] = useState<string>("");
  const [isSavingWorkflow, setIsSavingWorkflow] = useState(false);

  useEffect(() => {
    if (agentName) {
      loadAgent();
      loadSubAgents();
      loadAvailableAgents();
    }
  }, [agentName]);

  useEffect(() => {
    if (workflowType === "custom") {
      if (customConfigText.trim()) {
        return;
      }

      if (workflowConfig) {
        try {
          const normalized =
            typeof workflowConfig === "string"
              ? JSON.parse(workflowConfig)
              : workflowConfig;
          setCustomConfigText(JSON.stringify(normalized, null, 2));
        } catch (error) {
          if (typeof workflowConfig === "string") {
            setCustomConfigText(workflowConfig);
          }
        }
      }
    }
  }, [workflowType, workflowConfig, customConfigText]);

  const loadAgent = async () => {
    try {
      const data = await apiClient.getAgent(agentName);
      setAgent(data);
      
      // Load workflow configuration
      if (data.workflow_type) {
        setWorkflowType(data.workflow_type);
      }
      if (data.workflow_config) {
        setWorkflowConfig(data.workflow_config);
        if (data.workflow_type === "custom") {
          try {
            const normalized =
              typeof data.workflow_config === "string"
                ? JSON.parse(data.workflow_config)
                : data.workflow_config;
            setCustomConfigText(JSON.stringify(normalized, null, 2));
          } catch (error) {
            if (typeof data.workflow_config === "string") {
              setCustomConfigText(data.workflow_config);
            }
          }
        }
      }
    } catch (error) {
      console.error('Failed to load agent:', error);
    }
  };

  const loadSubAgents = async () => {
    try {
      const response = await apiClient.request('GET', `/api/v1/agents/${agentName}/sub-agents`);
      if (response.success) {
        setSubAgents(response.data.sub_agents || []);
      }
    } catch (error: any) {
      console.error("Failed to load sub-agents:", error);
      toast.error(error.response?.data?.message || "Failed to load sub-agents");
    } finally {
      setLoading(false);
    }
  };

  const loadAvailableAgents = async () => {
    try {
      const response = await apiClient.request('GET', `/api/v1/agents/${agentName}/sub-agents/available`);
      if (response.success) {
        setAvailableAgents(response.data.available_agents || []);
      }
    } catch (error: any) {
      console.error("Failed to load available agents:", error);
    }
  };

  const handleAddSubAgent = async () => {
    if (!selectedAgentId) {
      toast.error("Please select an agent");
      return;
    }

    try {
      const response = await apiClient.request('POST', `/api/v1/agents/${agentName}/sub-agents`, {
        sub_agent_id: selectedAgentId,
        execution_order: executionOrder,
      });

      if (response.success) {
        toast.success("Sub-agent added successfully");
        setShowAddDialog(false);
        setSelectedAgentId("");
        setExecutionOrder(0);
        await loadSubAgents();
        await loadAvailableAgents();
      }
    } catch (error: any) {
      console.error("Failed to add sub-agent:", error);
      toast.error(error.response?.data?.message || "Failed to add sub-agent");
    }
  };

  const handleRemoveSubAgent = async (subAgentId: string, name: string) => {
    if (!confirm(`Are you sure you want to remove "${name}" as a sub-agent?`)) {
      return;
    }

    try {
      const response = await apiClient.request('DELETE', `/api/v1/agents/${agentName}/sub-agents/${subAgentId}`);

      if (response.success) {
        toast.success("Sub-agent removed successfully");
        await loadSubAgents();
        await loadAvailableAgents();
      }
    } catch (error: any) {
      console.error("Failed to remove sub-agent:", error);
      toast.error(error.response?.data?.message || "Failed to remove sub-agent");
    }
  };

  const handleToggleActive = async (subAgentId: string, currentStatus: boolean) => {
    try {
      const response = await apiClient.request('PATCH', `/api/v1/agents/${agentName}/sub-agents/${subAgentId}`, {
        is_active: !currentStatus
      });

      if (response.success) {
        toast.success("Status updated successfully");
        await loadSubAgents();
      }
    } catch (error: any) {
      console.error("Failed to update status:", error);
      toast.error(error.response?.data?.message || "Failed to update status");
    }
  };

  const handleUpdateOrder = async (subAgentId: string, newOrder: number) => {
    try {
      const response = await apiClient.request('PATCH', `/api/v1/agents/${agentName}/sub-agents/${subAgentId}`, {
        execution_order: newOrder
      });

      if (response.success) {
        toast.success("Order updated successfully");
        await loadSubAgents();
      }
    } catch (error: any) {
      console.error("Failed to update order:", error);
      toast.error(error.response?.data?.message || "Failed to update order");
    }
  };

  const handleSaveWorkflowConfig = async () => {
    setIsSavingWorkflow(true);
    try {
      let payloadConfig = workflowType ? { ...workflowConfig } : null;
      
      if (workflowType === "custom") {
        try {
          const customData = customConfigText ? JSON.parse(customConfigText) : {};
          // Merge form fields with custom config (custom config takes precedence for overlapping keys)
          const mergedConfig = {
            max_iterations: workflowConfig.max_iterations,
            timeout_seconds: workflowConfig.timeout_seconds,
            continue_on_error: workflowConfig.continue_on_error,
            aggregate_outputs: workflowConfig.aggregate_outputs,
            ...customData
          };
          payloadConfig = mergedConfig;
          setWorkflowConfig(mergedConfig);
        } catch (parseError) {
          toast.error("Custom config must be valid JSON");
          return;
        }
      }

      const response = await apiClient.request('PUT', `/api/v1/agents/${agentName}`, {
        workflow_type: workflowType || null,
        workflow_config: payloadConfig
      });

      if (response.success) {
        toast.success("Workflow configuration saved successfully");
        await loadAgent();
      }
    } catch (error: any) {
      console.error("Failed to save workflow config:", error);
      toast.error(error.response?.data?.message || "Failed to save workflow configuration");
    } finally {
      setIsSavingWorkflow(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-red-50/30 to-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 text-sm">Loading sub-agents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/agents/${agentName}/view`)}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Sub-Agents Configuration</h1>
              <p className="text-sm text-gray-600 mt-1">
                Configure sub-agents for <span className="font-semibold">{agent?.agent_name || agentName}</span>
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowAddDialog(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all font-medium shadow-sm"
          >
            <Plus className="w-5 h-5" />
            Add Sub-Agent
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-6">
        {/* Workflow Configuration Card */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-6">
          <div className="px-5 py-3 border-b border-gray-200 bg-gradient-to-r from-red-50 to-red-100/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-red-100 rounded-md">
                  <Workflow className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-900">Workflow Configuration</h2>
                  <p className="text-xs text-gray-600">
                    Configure how sub-agents are orchestrated and executed
                  </p>
                </div>
              </div>
              <button
                onClick={handleSaveWorkflowConfig}
                disabled={isSavingWorkflow}
                className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all text-xs font-medium shadow-sm disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {isSavingWorkflow ? "Saving..." : "Save Config"}
              </button>
            </div>
          </div>

          <div className="p-5 space-y-4">
            {/* Workflow Type Selection */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Workflow Type
              </label>
              <select
                value={workflowType}
                onChange={(e) => setWorkflowType(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
              >
                <option value="">None (Standard Agent)</option>
                <option value="sequential">Sequential - Execute sub-agents one after another</option>
                <option value="parallel">Parallel - Execute sub-agents concurrently</option>
                <option value="loop">Loop - Iterative execution with refinement</option>
                <option value="custom">Custom - Specialized orchestration flow</option>
              </select>
              <p className="text-xs text-gray-500">
                {workflowType === "" && "This agent will function as a standard agent without workflow orchestration."}
                {workflowType === "sequential" && "Sub-agents will execute in order. Output of one agent becomes input to the next."}
                {workflowType === "parallel" && "All sub-agents execute simultaneously. Results are aggregated."}
                {workflowType === "loop" && "Sub-agents execute iteratively until convergence or max iterations."}
                {workflowType === "custom" && "Custom flow is defined by a JSON nodes config."}
              </p>
            </div>

            {/* Workflow Configuration Options (shown when workflow type is selected) */}
            {workflowType && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Max Iterations
                  </label>
                  <Input
                    type="number"
                    value={workflowConfig.max_iterations}
                    onChange={(e) => setWorkflowConfig({
                      ...workflowConfig,
                      max_iterations: parseInt(e.target.value) || 10
                    })}
                    className="w-full px-3 py-2 text-sm focus:ring-red-500"
                  />
                  <p className="text-xs text-gray-500">
                    Maximum iterations for loop/custom workflows
                  </p>
                </div>

                {workflowType === "custom" && (
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Custom Workflow Config (JSON)
                    </label>
                    <textarea
                      value={customConfigText}
                      onChange={(e) => setCustomConfigText(e.target.value)}
                      rows={8}
                      className="w-full px-3 py-2 text-xs font-mono border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    />
                    <p className="text-xs text-gray-500">
                      Example: {"{\"nodes\":[{\"type\":\"agent\",\"agents\":[\"story_generator\"]},{\"type\":\"loop\",\"agents\":[\"critic\",\"reviser\"],\"iterations\":2},{\"type\":\"sequential\",\"agents\":[\"grammar_check\",\"tone_check\"]}],\"stop_on_error\":true}"}
                    </p>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Timeout (seconds)
                  </label>
                  <Input
                    type="number"
                    value={workflowConfig.timeout_seconds}
                    onChange={(e) => setWorkflowConfig({
                      ...workflowConfig,
                      timeout_seconds: parseInt(e.target.value) || 300
                    })}
                    className="w-full px-3 py-2 text-sm focus:ring-red-500"
                  />
                  <p className="text-xs text-gray-500">
                    Maximum execution time for the entire workflow
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={workflowConfig.continue_on_error}
                      onChange={(e) => setWorkflowConfig({
                        ...workflowConfig,
                        continue_on_error: e.target.checked
                      })}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      Continue on Error
                    </span>
                  </label>
                  <p className="text-xs text-gray-500 ml-6">
                    Continue executing remaining sub-agents if one fails
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={workflowConfig.aggregate_outputs}
                      onChange={(e) => setWorkflowConfig({
                        ...workflowConfig,
                        aggregate_outputs: e.target.checked
                      })}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                    <span className="text-sm font-medium text-gray-700">
                      Aggregate Outputs
                    </span>
                  </label>
                  <p className="text-xs text-gray-500 ml-6">
                    Combine outputs from all sub-agents into final response
                  </p>
                </div>
              </div>
            )}

            {/* Workflow Status Indicator */}
            <div className="flex items-center gap-2 pt-3 border-t border-gray-200">
              <Settings className="w-4 h-4 text-gray-400" />
              <span className="text-xs text-gray-600">
                {workflowType ? (
                  <span className="font-medium text-red-600">
                    Workflow Mode: {workflowType.charAt(0).toUpperCase() + workflowType.slice(1)}
                  </span>
                ) : (
                  "Standard agent mode - select a workflow type to enable multi-agent orchestration"
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
          <div className="bg-white rounded-xl shadow-sm p-4 border border-gray-200">
            <div className="text-xs text-gray-600">Total Sub-Agents</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">
              {subAgents.length}
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4 border border-gray-200">
            <div className="text-xs text-gray-600">Active Sub-Agents</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">
              {subAgents.filter(t => t.is_active).length}
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-4 border border-gray-200">
            <div className="text-xs text-gray-600">Available to Add</div>
            <div className="text-2xl font-bold text-red-600 mt-1">
              {availableAgents.length}
            </div>
          </div>
        </div>

        {/* Sub-Agents List */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-red-100 rounded-md">
                <Users className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-gray-900">Configured Sub-Agents</h2>
                <p className="text-xs text-gray-600">
                  Sub-agents are executed in order when called by the parent agent
                </p>
              </div>
            </div>
          </div>

          {subAgents.length === 0 ? (
            <div className="p-10 text-center">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-6 h-6 text-red-400" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">No Sub-Agents Configured</h3>
              <p className="text-gray-600 text-sm mb-4 max-w-md mx-auto">
                Add sub-agents to enable this agent to delegate tasks to specialized agents
              </p>
              <button
                onClick={() => setShowAddDialog(true)}
                className="inline-flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all text-xs font-medium shadow-sm"
              >
                <Plus className="w-4 h-4" />
                Add Your First Sub-Agent
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-red-50">
                  <tr>
                    <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Order
                    </th>
                    <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Agent Name
                    </th>
                    <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-5 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-5 py-2.5 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {subAgents.map((subAgent, index) => (
                    <tr key={subAgent.id} className="hover:bg-red-50 transition-colors">
                      <td className="px-5 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-medium bg-red-100 text-red-700 px-2 py-1 rounded">
                            {subAgent.execution_order}
                          </span>
                          <div className="flex flex-col gap-0.5">
                            <button
                              disabled={index === 0}
                              onClick={() =>
                                handleUpdateOrder(
                                  subAgent.id,
                                  subAgent.execution_order - 1
                                )
                              }
                              className="p-0.5 hover:bg-red-100 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            >
                              <ArrowUp className="w-3 h-3" />
                            </button>
                            <button
                              disabled={index === subAgents.length - 1}
                              onClick={() =>
                                handleUpdateOrder(
                                  subAgent.id,
                                  subAgent.execution_order + 1
                                )
                              }
                              className="p-0.5 hover:bg-red-100 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            >
                              <ArrowDown className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {subAgent.sub_agent_name}
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <div className="text-xs text-gray-600 max-w-md truncate">
                          {subAgent.sub_agent_description || "-"}
                        </div>
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() =>
                              handleToggleActive(subAgent.id, subAgent.is_active)
                            }
                            className={`p-1.5 rounded-lg transition-colors ${
                              subAgent.is_active
                                ? 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'
                                : 'bg-gray-200 text-gray-400 hover:bg-gray-300'
                            }`}
                          >
                            {subAgent.is_active ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                          </button>
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              subAgent.is_active
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {subAgent.is_active ? "Active" : "Inactive"}
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3 whitespace-nowrap text-right">
                        <button
                          onClick={() =>
                            handleRemoveSubAgent(
                              subAgent.id,
                              subAgent.sub_agent_name
                            )
                          }
                          className="p-1.5 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Add Sub-Agent Modal */}
      <Modal
        isOpen={showAddDialog}
        onClose={() => setShowAddDialog(false)}
        title="Add Sub-Agent"
      >
        <div className="space-y-4">
          <p className="text-xs text-gray-600">
            Select an agent to add as a sub-agent for "{agentName}"
          </p>

          <div className="space-y-2">
            <label className="block text-xs font-medium text-gray-700">
              Agent
            </label>
            <select
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            >
              <option value="">Select an agent</option>
              {availableAgents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.agent_name}
                  {agent.description && ` - ${agent.description}`}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-medium text-gray-700">
              Execution Order
            </label>
            <Input
              type="number"
              value={executionOrder}
              onChange={(e) => setExecutionOrder(parseInt(e.target.value) || 0)}
              placeholder="0"
              className="w-full px-3 py-2 text-sm focus:ring-red-500"
            />
            <p className="text-xs text-gray-500">
              Lower numbers execute first. Use same number for parallel execution (future feature).
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <button
              onClick={() => setShowAddDialog(false)}
              className="px-4 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-white hover:border-red-300 transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              onClick={handleAddSubAgent}
              className="px-4 py-2 text-sm bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg hover:from-red-600 hover:to-red-700 transition-all font-medium shadow-sm"
            >
              Add Sub-Agent
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
