import { describe, it, expect, beforeEach } from "vitest";
import {
  generateSessionId,
  generateSessionTitle,
  getAllSessions,
  getSession,
  saveSession,
  deleteSession,
  getRecentSessions,
  type ChatSession,
} from "../chatHistory";

// jsdom provides localStorage; clear it before each test
beforeEach(() => {
  localStorage.clear();
});

function makeSession(overrides: Partial<ChatSession> = {}): ChatSession {
  return {
    id: generateSessionId(),
    title: "Test Session",
    agentName: "test-agent",
    messages: [],
    timestamp: new Date(),
    createdAt: new Date(),
    ...overrides,
  };
}

describe("generateSessionId", () => {
  it("returns a non-empty string starting with 'session_'", () => {
    const id = generateSessionId();
    expect(typeof id).toBe("string");
    expect(id.startsWith("session_")).toBe(true);
  });

  it("generates unique IDs", () => {
    const ids = new Set(Array.from({ length: 20 }, generateSessionId));
    expect(ids.size).toBe(20);
  });
});

describe("generateSessionTitle", () => {
  it("returns 'New Chat' for an empty messages array", () => {
    expect(generateSessionTitle([])).toBe("New Chat");
  });

  it("returns 'New Chat' when there is no user message", () => {
    expect(generateSessionTitle([{ role: "assistant", content: "Hello" }])).toBe(
      "New Chat"
    );
  });

  it("returns the full content when it is 50 chars or fewer", () => {
    const content = "Short message";
    expect(generateSessionTitle([{ role: "user", content }])).toBe(content);
  });

  it("truncates content longer than 50 characters", () => {
    const content = "A".repeat(60);
    const title = generateSessionTitle([{ role: "user", content }]);
    expect(title).toHaveLength(50);
    expect(title.endsWith("...")).toBe(true);
  });
});

describe("getAllSessions", () => {
  it("returns an empty array when nothing is stored", () => {
    expect(getAllSessions("agent")).toEqual([]);
  });

  it("returns sessions with Date objects", () => {
    const session = makeSession();
    saveSession("agent", session);
    const result = getAllSessions("agent");
    expect(result[0].timestamp).toBeInstanceOf(Date);
    expect(result[0].createdAt).toBeInstanceOf(Date);
  });
});

describe("saveSession / getSession", () => {
  it("stores and retrieves a session by ID", () => {
    const s = makeSession({ id: "sess_001", title: "My Chat" });
    saveSession("agent", s);
    const retrieved = getSession("agent", "sess_001");
    expect(retrieved).not.toBeNull();
    expect(retrieved!.title).toBe("My Chat");
  });

  it("updates an existing session", () => {
    const s = makeSession({ id: "sess_002", title: "Original" });
    saveSession("agent", s);
    saveSession("agent", { ...s, title: "Updated" });
    const all = getAllSessions("agent");
    expect(all.filter((x) => x.id === "sess_002")).toHaveLength(1);
    expect(all.find((x) => x.id === "sess_002")!.title).toBe("Updated");
  });

  it("returns null for a non-existent session ID", () => {
    expect(getSession("agent", "nonexistent")).toBeNull();
  });

  it("isolates sessions by agentName", () => {
    const s = makeSession({ id: "sess_003" });
    saveSession("agent-a", s);
    expect(getSession("agent-b", "sess_003")).toBeNull();
  });
});

describe("deleteSession", () => {
  it("removes a session from storage", () => {
    const s = makeSession({ id: "sess_del" });
    saveSession("agent", s);
    deleteSession("agent", "sess_del");
    expect(getSession("agent", "sess_del")).toBeNull();
  });

  it("does not throw when deleting a non-existent session", () => {
    expect(() => deleteSession("agent", "ghost")).not.toThrow();
  });
});

describe("getRecentSessions", () => {
  it("returns sessions sorted by most recent timestamp", () => {
    const older = makeSession({
      id: "old",
      timestamp: new Date(Date.now() - 10_000),
    });
    const newer = makeSession({
      id: "new",
      timestamp: new Date(Date.now()),
    });
    saveSession("agent", older);
    saveSession("agent", newer);
    const recent = getRecentSessions("agent", 10);
    expect(recent[0].id).toBe("new");
  });

  it("respects the limit parameter", () => {
    for (let i = 0; i < 5; i++) {
      saveSession("agent", makeSession({ id: `sess_${i}` }));
    }
    expect(getRecentSessions("agent", 3)).toHaveLength(3);
  });
});
