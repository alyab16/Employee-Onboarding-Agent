"use client";

import { useEffect, useRef, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { useChat } from "../hooks/useChat";
import type { Employee } from "../types";

interface Props {
  employee: Employee;
  onLogout: () => void;
}

const SUGGESTED_PROMPTS = [
  "Let's get started with my onboarding!",
  "What do I need to do today?",
  "Can you update all my profiles?",
  "What system access will I need?",
];

export function ChatInterface({ employee, onLogout }: Props) {
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    respondToApproval,
    clearHistory,
  } = useChat(employee.id);
  const [input, setInput] = useState("");
  const [chatKey, setChatKey] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const hasStarted = messages.length > 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const greetedRef = useRef(false);
  useEffect(() => {
    if (greetedRef.current) return;
    greetedRef.current = true;
    sendMessage("Hello! I'm ready to start my onboarding.");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employee.id, chatKey]);

  const awaitingApproval = messages.some((m) => m.awaitingApproval);
  const inputDisabled = isLoading || awaitingApproval;

  const handleSend = () => {
    const text = input.trim();
    if (!text || inputDisabled) return;
    setInput("");
    sendMessage(text);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-stone-50">
      {/* Header — compact, minimal */}
      <header className="flex-shrink-0 flex items-center justify-between px-5 py-2.5 bg-white border-b border-stone-200">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-stone-800 flex items-center justify-center text-white font-bold text-[10px]">
            {employee.name
              .split(" ")
              .map((n) => n[0])
              .join("")}
          </div>
          <div>
            <p className="font-semibold text-stone-900 text-sm leading-tight">
              {employee.name}
            </p>
            <p className="text-[11px] text-stone-400">
              {employee.role} · {employee.level} · {employee.department}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              clearHistory();
              greetedRef.current = false;
              setChatKey((k) => k + 1);
            }}
            className="text-[11px] text-stone-400 hover:text-stone-700 px-2.5 py-1 rounded-md hover:bg-stone-100 transition-all"
          >
            Restart
          </button>
          <div className="w-px h-3 bg-stone-200" />
          <button
            onClick={onLogout}
            className="text-[11px] text-stone-400 hover:text-stone-700 px-2.5 py-1 rounded-md hover:bg-stone-100 transition-all"
          >
            Switch
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
        {!hasStarted && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white text-lg">
              AI
            </div>
            <p className="text-sm text-stone-500">
              Connecting to your onboarding assistant...
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isBusy={isLoading}
            onApprove={(edited_args) =>
              respondToApproval({ approved: true, edited_args })
            }
            onReject={(reason) =>
              respondToApproval({ approved: false, reason })
            }
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="flex-shrink-0 mx-5 mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-red-600 text-xs">
          {error}
        </div>
      )}

      {/* Suggested prompts */}
      {!isLoading && messages.length > 0 && messages.length < 3 && (
        <div className="flex-shrink-0 px-5 pb-2 flex gap-1.5 flex-wrap">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => sendMessage(prompt)}
              className="text-[11px] px-2.5 py-1 rounded-md border border-stone-200 text-stone-500
                bg-white hover:bg-stone-50 hover:text-stone-700 hover:border-stone-300 transition-all"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex-shrink-0 px-5 py-3 bg-white border-t border-stone-200">
        <div className="flex items-end gap-2 bg-stone-50 rounded-xl border border-stone-200 px-3 py-2.5 focus-within:border-teal-500 focus-within:ring-1 focus-within:ring-teal-500/20 transition-all">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={awaitingApproval ? "Resolve the approval above to continue..." : "Type a message..."}
            rows={1}
            disabled={inputDisabled}
            className="flex-1 bg-transparent resize-none outline-none text-sm text-stone-800 placeholder-stone-400 max-h-28 disabled:opacity-50"
            style={{ height: "auto" }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = `${el.scrollHeight}px`;
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || inputDisabled}
            className="flex-shrink-0 w-7 h-7 rounded-lg bg-teal-600 text-white flex items-center justify-center
              hover:bg-teal-700 disabled:opacity-25 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <span className="w-3 h-3 border-[1.5px] border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M5 12h14M12 5l7 7-7 7"
                />
              </svg>
            )}
          </button>
        </div>
        <p className="text-[10px] text-stone-400 mt-1.5 text-center">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
