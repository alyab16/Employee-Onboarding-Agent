"use client";

import { useCallback, useRef, useState } from "react";
import type {
  AgentEvent,
  Message,
  PendingApproval,
  SpecialistHandoff,
  ToolActivity,
} from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

/** Mutable in-flight state for the assistant message currently streaming. */
interface StreamBuffer {
  assistantId: string;
  activities: ToolActivity[];
  handoffs: SpecialistHandoff[];
  approvals: PendingApproval[];
  pendingTool: Omit<ToolActivity, "output"> | null;
}

export function useChat(employeeId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  /** Id of the assistant message currently waiting on an approval, if any. */
  const awaitingIdRef = useRef<string | null>(null);

  const applyEvent = useCallback(
    (event: AgentEvent, buf: StreamBuffer): "continue" | "paused" | "done" => {
      switch (event.type) {
        case "text_delta":
          setMessages((prev) =>
            prev.map((m) =>
              m.id === buf.assistantId
                ? { ...m, content: m.content + event.content }
                : m,
            ),
          );
          return "continue";

        case "agent_handoff":
          if (
            buf.handoffs.length === 0 ||
            buf.handoffs[buf.handoffs.length - 1].specialist !== event.specialist
          ) {
            buf.handoffs = [
              ...buf.handoffs,
              { specialist: event.specialist, label: event.label },
            ];
            setMessages((prev) =>
              prev.map((m) =>
                m.id === buf.assistantId ? { ...m, handoffs: buf.handoffs } : m,
              ),
            );
          }
          return "continue";

        case "tool_call":
          buf.pendingTool = {
            tool: event.tool,
            server: event.server,
            input: event.input,
          };
          return "continue";

        case "tool_result":
          if (buf.pendingTool) {
            buf.activities = [
              ...buf.activities,
              { ...buf.pendingTool, output: event.output },
            ];
            buf.pendingTool = null;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === buf.assistantId
                  ? { ...m, toolActivities: buf.activities }
                  : m,
              ),
            );
          }
          return "continue";

        case "approval_required": {
          const approval: PendingApproval = {
            interruptId: event.interrupt_id,
            tool: event.tool,
            server: event.server,
            action: event.action,
            args: event.args,
            status: "pending",
          };
          buf.approvals = [...buf.approvals, approval];
          setMessages((prev) =>
            prev.map((m) =>
              m.id === buf.assistantId
                ? {
                    ...m,
                    approvals: buf.approvals,
                    awaitingApproval: true,
                    isStreaming: false,
                  }
                : m,
            ),
          );
          return "continue";
        }

        case "awaiting_approval":
          awaitingIdRef.current = buf.assistantId;
          return "paused";

        case "done":
          setMessages((prev) =>
            prev.map((m) =>
              m.id === buf.assistantId
                ? { ...m, isStreaming: false, awaitingApproval: false }
                : m,
            ),
          );
          awaitingIdRef.current = null;
          return "done";

        case "error":
          setError(event.message);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === buf.assistantId
                ? {
                    ...m,
                    content:
                      m.content ||
                      "Sorry, an error occurred. Please try again.",
                    isStreaming: false,
                    awaitingApproval: false,
                  }
                : m,
            ),
          );
          return "done";
      }
    },
    [],
  );

  const consumeStream = useCallback(
    async (response: Response, buf: StreamBuffer) => {
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let textBuffer = "";
      let terminal: "paused" | "done" = "done";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        textBuffer += decoder.decode(value, { stream: true });
        const lines = textBuffer.split("\n");
        textBuffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let event: AgentEvent;
          try {
            event = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          const result = applyEvent(event, buf);
          if (result === "paused") {
            terminal = "paused";
            // Drain remaining lines but expect none.
          } else if (result === "done") {
            terminal = "done";
          }
        }
      }

      return terminal;
    },
    [applyEvent],
  );

  const sendMessage = useCallback(
    async (userText: string) => {
      if (!employeeId || !userText.trim() || isLoading) return;
      setError(null);

      const userMsg: Message = {
        id: makeId(),
        role: "user",
        content: userText.trim(),
      };
      setMessages((prev) => [...prev, userMsg]);

      const assistantId = makeId();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          toolActivities: [],
          handoffs: [],
          approvals: [],
          isStreaming: true,
        },
      ]);

      setIsLoading(true);
      abortRef.current = new AbortController();

      const buf: StreamBuffer = {
        assistantId,
        activities: [],
        handoffs: [],
        approvals: [],
        pendingTool: null,
      };

      try {
        const response = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            employee_id: employeeId,
            message: userText.trim(),
          }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`Server error: ${response.status}`);
        }

        await consumeStream(response, buf);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: "Connection error. Is the backend running?",
                  isStreaming: false,
                  awaitingApproval: false,
                }
              : m,
          ),
        );
      } finally {
        setIsLoading(false);
      }
    },
    [employeeId, isLoading, consumeStream],
  );

  const respondToApproval = useCallback(
    async (decision: {
      approved: boolean;
      reason?: string;
      edited_args?: Record<string, unknown>;
    }) => {
      if (!employeeId) return;
      const assistantId = awaitingIdRef.current;
      if (!assistantId) return;

      const current = messages.find((m) => m.id === assistantId);
      if (!current) return;

      // Mark the last approval resolved. Compute once so both the React state
      // update and the stream buffer share the same array — otherwise a second
      // approval_required event from the resumed stream would overwrite state
      // with a stale "pending" snapshot and the card would never clear.
      const prevApprovals = current.approvals ?? [];
      const nextApprovals: PendingApproval[] = prevApprovals.map((a, i) =>
        i === prevApprovals.length - 1
          ? {
              ...a,
              args: { ...a.args, ...(decision.edited_args ?? {}) },
              status: decision.approved ? "approved" : "rejected",
              reason: decision.reason,
            }
          : a,
      );

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                approvals: nextApprovals,
                awaitingApproval: false,
                isStreaming: true,
              }
            : m,
        ),
      );

      setIsLoading(true);
      abortRef.current = new AbortController();

      const buf: StreamBuffer = {
        assistantId,
        activities: current.toolActivities ?? [],
        handoffs: current.handoffs ?? [],
        approvals: nextApprovals,
        pendingTool: null,
      };

      try {
        const response = await fetch(`${API_BASE}/api/chat/resume`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            employee_id: employeeId,
            approved: decision.approved,
            reason: decision.reason ?? "",
            edited_args: decision.edited_args ?? {},
          }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`Server error: ${response.status}`);
        }

        await consumeStream(response, buf);
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [employeeId, messages, consumeStream],
  );

  const clearHistory = useCallback(async () => {
    abortRef.current?.abort();
    awaitingIdRef.current = null;
    setMessages([]);
    setError(null);
    setIsLoading(false);

    if (!employeeId) return;
    // Wipe backend checkpointed state so the next turn starts clean. Without
    // this, the supervisor sees stale history (and possibly a pending HITL
    // interrupt) and the next message can return an empty response.
    try {
      await fetch(
        `${API_BASE}/api/chat/history?employee_id=${encodeURIComponent(employeeId)}`,
        { method: "DELETE" },
      );
    } catch {
      // Best-effort — UI is already cleared.
    }
  }, [employeeId]);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    respondToApproval,
    clearHistory,
  };
}
