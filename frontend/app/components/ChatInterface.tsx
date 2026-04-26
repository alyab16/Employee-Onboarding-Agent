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
      <header className="flex-shrink-0 flex items-center justify-between px-5 py-2.5 bg-white/90 backdrop-blur-sm border-b border-stone-200">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-stone-700 to-stone-900 flex items-center justify-center text-white font-bold text-[10px] shadow-sm ring-1 ring-stone-900/10">
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
          <span className="ml-2 inline-flex items-center gap-1 text-[10px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
            </span>
            Online
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={async () => {
              await clearHistory();
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
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4 chat-backdrop chat-scroll">
        {!hasStarted && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center animate-fade-in-up">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-teal-500 via-teal-600 to-emerald-600 flex items-center justify-center text-white shadow-md ring-1 ring-teal-900/10">
              <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2M12 19v2M5 12H3M21 12h-2M6 6l1.5 1.5M16.5 16.5 18 18M6 18l1.5-1.5M16.5 7.5 18 6" />
                <circle cx="12" cy="12" r="4" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-stone-700">
                Your onboarding assistant
              </p>
              <p className="text-xs text-stone-400 mt-0.5">
                Connecting securely...
              </p>
            </div>
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
            className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 text-white flex items-center justify-center shadow-sm
              hover:shadow-md hover:from-teal-600 hover:to-emerald-700 active:scale-95 disabled:opacity-25 disabled:cursor-not-allowed transition-all"
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
