"use client";

import { useState } from "react";
import type { Message, ToolActivity } from "../types";
import { SERVER_COLORS, SERVER_LABELS } from "../types";

/** Safely extract a renderable string — handles LangGraph content block objects. */
function safeString(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  if (Array.isArray(value)) {
    return value
      .map((v) =>
        typeof v === "object" && v !== null && "text" in v
          ? (v as { text: string }).text
          : String(v),
      )
      .join("");
  }
  if (typeof value === "object" && "text" in value)
    return String((value as { text: string }).text);
  return JSON.stringify(value);
}

function ToolActivityCard({ activity }: { activity: ToolActivity }) {
  const [expanded, setExpanded] = useState(false);
  const colors = SERVER_COLORS[activity.server] ?? SERVER_COLORS.unknown;
  const serverLabel = SERVER_LABELS[activity.server] ?? activity.server;

  return (
    <div
      className={`rounded-md border border-stone-200 text-xs transition-all ${expanded ? "shadow-sm" : ""}`}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-stone-50 transition-colors rounded-md"
      >
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${colors.dot}`} />
        <span className="font-mono text-stone-700">{activity.tool}</span>
        <span className={`ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
          {serverLabel}
        </span>
        <svg
          className={`w-3 h-3 text-stone-400 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-stone-100 px-3 py-2 space-y-2 bg-stone-50/50">
          {Object.keys(activity.input).length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-stone-400 uppercase tracking-wider mb-1">
                Input
              </p>
              <pre className="whitespace-pre-wrap break-all text-stone-600 text-[11px] leading-relaxed font-mono">
                {JSON.stringify(activity.input, null, 2)}
              </pre>
            </div>
          )}
          {activity.output && (
            <div>
              <p className="text-[10px] font-semibold text-stone-400 uppercase tracking-wider mb-1">
                Output
              </p>
              <pre className="whitespace-pre-wrap break-all text-stone-600 text-[11px] leading-relaxed font-mono max-h-40 overflow-y-auto">
                {safeString(activity.output)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  const displayContent = safeString(message.content);

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold
          ${isUser
            ? "bg-stone-800 text-white"
            : "bg-teal-600 text-white"
          }`}
      >
        {isUser ? "You" : "AI"}
      </div>

      <div
        className={`flex flex-col gap-1.5 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}
      >
        {/* Tool activity cards */}
        {!isUser &&
          message.toolActivities &&
          message.toolActivities.length > 0 && (
            <div className="w-full space-y-1">
              {message.toolActivities.map((activity, i) => (
                <ToolActivityCard key={i} activity={activity} />
              ))}
            </div>
          )}

        {/* Message text */}
        {(displayContent || message.isStreaming) && (
          <div
            className={`rounded-xl px-3.5 py-2.5 text-[13px] leading-relaxed whitespace-pre-wrap
              ${isUser
                ? "bg-stone-800 text-stone-100"
                : "bg-white text-stone-700 border border-stone-200 shadow-sm"
              }`}
          >
            {displayContent}
            {message.isStreaming && !displayContent && (
              <span className="text-stone-400 text-xs">Thinking...</span>
            )}
            {message.isStreaming && displayContent && (
              <span className="inline-block w-[3px] h-[14px] bg-teal-500 ml-0.5 align-middle animate-pulse rounded-full" />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
