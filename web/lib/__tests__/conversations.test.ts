import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

// Mock the http module so that apiClient.axios is a controlled stub.
// All functions in conversations.ts import `apiClient` from './http'.
vi.mock("../api/http", () => {
  const axios = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  };
  return {
    apiClient: { axios },
    APIClient: class {},
  };
});

// Also stub the global fetch used by getSharedConversation
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import {
  getConversations,
  createConversation,
  deleteConversation,
  getAgentConversations,
  createAgentConversation,
  getConversationById,
  updateConversationName,
  deleteAgentConversation,
  getConversationMessages,
  sendMessage,
  getMessages,
  createConversationShare,
  listConversationShares,
  revokeConversationShare,
  getSharedConversation,
} from "../api/conversations";

import { apiClient } from "../api/http";

// Typed shorthand so tests read cleanly
const ax = (apiClient as any).axios as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── Legacy conversations ──────────────────────────────────────────────────────

describe("getConversations", () => {
  it("calls GET /console/api/apps/:appId/conversations and returns data", async () => {
    const payload = [{ id: "c1" }, { id: "c2" }];
    ax.get.mockResolvedValue({ data: payload });

    const result = await getConversations("app-99");

    expect(ax.get).toHaveBeenCalledWith("/console/api/apps/app-99/conversations");
    expect(result).toEqual(payload);
  });
});

describe("createConversation", () => {
  it("calls POST /console/api/apps/:appId/conversations and returns data", async () => {
    const created = { id: "new-c" };
    ax.post.mockResolvedValue({ data: created });

    const result = await createConversation("app-42");

    expect(ax.post).toHaveBeenCalledWith("/console/api/apps/app-42/conversations");
    expect(result).toEqual(created);
  });
});

describe("deleteConversation", () => {
  it("calls DELETE /console/api/conversations/:id", async () => {
    ax.delete.mockResolvedValue({});

    await deleteConversation("conv-7");

    expect(ax.delete).toHaveBeenCalledWith("/console/api/conversations/conv-7");
  });
});

// ── Agent conversations ───────────────────────────────────────────────────────

describe("getAgentConversations", () => {
  it("calls GET with the correct agent URL and limit param", async () => {
    ax.get.mockResolvedValue({ data: { data: { conversations: [{ id: "c1" }] } } });

    const result = await getAgentConversations("agent-abc", 25);

    expect(ax.get).toHaveBeenCalledWith(
      "/api/v1/agents/agent-abc/conversations",
      { params: { limit: 25 } }
    );
    expect(result).toEqual([{ id: "c1" }]);
  });

  it("defaults to limit 50 when no limit is supplied", async () => {
    ax.get.mockResolvedValue({ data: { data: { conversations: [] } } });

    await getAgentConversations("agent-abc");

    expect(ax.get).toHaveBeenCalledWith(
      "/api/v1/agents/agent-abc/conversations",
      { params: { limit: 50 } }
    );
  });

  it("returns an empty array when conversations key is missing", async () => {
    ax.get.mockResolvedValue({ data: { data: {} } });
    const result = await getAgentConversations("agent-abc");
    expect(result).toEqual([]);
  });
});

describe("createAgentConversation", () => {
  it("posts to /api/v1/agents/conversations with agent_id and name", async () => {
    const conv = { id: "conv-new" };
    ax.post.mockResolvedValue({ data: { data: conv } });

    const result = await createAgentConversation("agent-1", "My Chat");

    expect(ax.post).toHaveBeenCalledWith("/api/v1/agents/conversations", {
      agent_id: "agent-1",
      name: "My Chat",
    });
    expect(result).toEqual(conv);
  });

  it("defaults name to 'New Conversation' when omitted", async () => {
    ax.post.mockResolvedValue({ data: { data: {} } });

    await createAgentConversation("agent-2");

    expect(ax.post).toHaveBeenCalledWith(
      "/api/v1/agents/conversations",
      expect.objectContaining({ name: "New Conversation" })
    );
  });
});

describe("getConversationById", () => {
  it("fetches conversation by ID with include_messages param", async () => {
    const conv = { id: "c-100", messages: [] };
    ax.get.mockResolvedValue({ data: { data: conv } });

    const result = await getConversationById("c-100", true);

    expect(ax.get).toHaveBeenCalledWith(
      "/api/v1/agents/conversations/c-100",
      { params: { include_messages: true } }
    );
    expect(result).toEqual(conv);
  });

  it("defaults include_messages to false", async () => {
    ax.get.mockResolvedValue({ data: { data: {} } });

    await getConversationById("c-200");

    expect(ax.get).toHaveBeenCalledWith(
      "/api/v1/agents/conversations/c-200",
      { params: { include_messages: false } }
    );
  });
});

describe("updateConversationName", () => {
  it("sends PUT with new name and returns updated data", async () => {
    ax.put.mockResolvedValue({ data: { data: { id: "c-5", name: "Renamed" } } });

    const result = await updateConversationName("c-5", "Renamed");

    expect(ax.put).toHaveBeenCalledWith("/api/v1/agents/conversations/c-5", {
      name: "Renamed",
    });
    expect(result).toEqual({ id: "c-5", name: "Renamed" });
  });
});

describe("deleteAgentConversation", () => {
  it("calls DELETE on the agent conversation endpoint", async () => {
    ax.delete.mockResolvedValue({});

    await deleteAgentConversation("c-999");

    expect(ax.delete).toHaveBeenCalledWith(
      "/api/v1/agents/conversations/c-999"
    );
  });
});

describe("getConversationMessages", () => {
  it("fetches messages with a limit param when provided", async () => {
    ax.get.mockResolvedValue({
      data: { data: { messages: [{ id: "m1" }] } },
    });

    const result = await getConversationMessages("c-1", 10);

    expect(ax.get).toHaveBeenCalledWith(
      "/api/v1/agents/conversations/c-1/messages",
      { params: { limit: 10 } }
    );
    expect(result).toEqual([{ id: "m1" }]);
  });

  it("sends no limit param when limit is not supplied", async () => {
    ax.get.mockResolvedValue({ data: { data: { messages: [] } } });

    await getConversationMessages("c-2");

    expect(ax.get).toHaveBeenCalledWith(
      "/api/v1/agents/conversations/c-2/messages",
      { params: {} }
    );
  });
});

// ── Legacy messages ───────────────────────────────────────────────────────────

describe("sendMessage", () => {
  it("posts to the legacy messages endpoint with content", async () => {
    const msg = { id: "m-5", content: "Hello" };
    ax.post.mockResolvedValue({ data: msg });

    const result = await sendMessage("c-legacy", "Hello");

    expect(ax.post).toHaveBeenCalledWith(
      "/console/api/conversations/c-legacy/messages",
      { content: "Hello" }
    );
    expect(result).toEqual(msg);
  });
});

describe("getMessages", () => {
  it("fetches messages from the legacy endpoint", async () => {
    const msgs = [{ id: "m-1" }, { id: "m-2" }];
    ax.get.mockResolvedValue({ data: msgs });

    const result = await getMessages("c-legacy");

    expect(ax.get).toHaveBeenCalledWith(
      "/console/api/conversations/c-legacy/messages"
    );
    expect(result).toEqual(msgs);
  });
});

// ── Conversation shares ───────────────────────────────────────────────────────

describe("createConversationShare", () => {
  it("posts to the shares endpoint with expires_in_seconds and returns the share", async () => {
    const share = { id: "s-1", share_url: "https://example.com/share/tok" };
    ax.post.mockResolvedValue({ data: { data: share } });

    const result = await createConversationShare("c-share", 86400);

    expect(ax.post).toHaveBeenCalledWith(
      "/api/v1/agents/conversations/c-share/shares",
      { expires_in_seconds: 86400 }
    );
    expect(result).toEqual(share);
  });
});

describe("listConversationShares", () => {
  it("fetches all shares for a conversation", async () => {
    const shares = [{ id: "s-1" }, { id: "s-2" }];
    ax.get.mockResolvedValue({ data: { data: { shares } } });

    const result = await listConversationShares("c-share");

    expect(ax.get).toHaveBeenCalledWith(
      "/api/v1/agents/conversations/c-share/shares"
    );
    expect(result).toEqual(shares);
  });

  it("returns empty array when shares key is missing", async () => {
    ax.get.mockResolvedValue({ data: { data: {} } });
    const result = await listConversationShares("c-share");
    expect(result).toEqual([]);
  });
});

describe("revokeConversationShare", () => {
  it("calls DELETE on the share endpoint", async () => {
    ax.delete.mockResolvedValue({});

    await revokeConversationShare("s-10", "c-share");

    expect(ax.delete).toHaveBeenCalledWith(
      "/api/v1/agents/conversations/c-share/shares/s-10"
    );
  });
});

describe("getSharedConversation", () => {
  it("fetches from the public share endpoint and returns data", async () => {
    const shareData = { conversation: {}, messages: [], agent: { name: "bot" } };
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ data: shareData }),
    });

    const result = await getSharedConversation("token-abc");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/public/share/token-abc")
    );
    expect(result).toEqual(shareData);
  });

  it("throws 'not_found' when the server returns 404", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 404 });

    await expect(getSharedConversation("bad-token")).rejects.toThrow("not_found");
  });

  it("throws 'fetch_error' for non-404 HTTP errors", async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 });

    await expect(getSharedConversation("tok")).rejects.toThrow("fetch_error");
  });
});
