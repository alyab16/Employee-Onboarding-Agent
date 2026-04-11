"use client";

import { useState, useCallback, useRef } from "react";
import type { Message, AgentEvent, ToolActivity } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

export function useChat(employeeId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (userText: string) => {
      if (!employeeId || !userText.trim() || isLoading) return;

      setError(null);

      // Add user message immediately
      const userMsg: Message = {
        id: makeId(),
        role: "user",
        content: userText.trim(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // Placeholder assistant message that will be filled by streaming
      const assistantId = makeId();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          toolActivities: [],
          isStreaming: true,
        },
      ]);

      setIsLoading(true);
      abortRef.current = new AbortController();

      try {
        const response = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ employee_id: employeeId, message: userText.trim() }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`Server error: ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentActivities: ToolActivity[] = [];
        let currentTool: Omit<ToolActivity, "output"> | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            let event: AgentEvent;
            try {
              event = JSON.parse(line.slice(6));
            } catch {
              continue;
            }

            if (event.type === "text_delta") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + event.content }
                    : m
                )
              );
            } else if (event.type === "tool_call") {
              currentTool = {
                tool: event.tool,
                server: event.server,
                input: event.input,
              };
            } else if (event.type === "tool_result" && currentTool) {
              const activity: ToolActivity = {
                ...currentTool,
                output: event.output,
              };
              currentActivities = [...currentActivities, activity];
              currentTool = null;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, toolActivities: currentActivities }
                    : m
                )
              );
            } else if (event.type === "done") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, isStreaming: false } : m
                )
              );
            } else if (event.type === "error") {
              setError(event.message);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: "Sorry, an error occurred. Please try again.", isStreaming: false }
                    : m
                )
              );
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: "Connection error. Is the backend running?", isStreaming: false }
              : m
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [employeeId, isLoading]
  );

  const clearHistory = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  return { messages, isLoading, error, sendMessage, clearHistory };
}
