"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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

/** Markdown renderer with Tailwind prose styles, sized to fit chat bubbles. */
function MarkdownContent({ content, isStreaming }: { content: string; isStreaming?: boolean }) {
  return (
    <div className="text-[13px] leading-relaxed text-stone-700">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p className="mb-2 last:mb-0">{children}</p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-stone-900">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-stone-600">{children}</em>
          ),
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-stone-900 mb-2 mt-3 first:mt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold text-stone-900 mb-1.5 mt-3 first:mt-0">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-[13px] font-semibold text-stone-800 mb-1 mt-2 first:mt-0">{children}</h3>
          ),
          ul: ({ children }) => (
            <ul className="mb-2 last:mb-0 space-y-0.5 pl-4">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2 last:mb-0 space-y-0.5 pl-4 list-decimal">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="relative pl-1 before:content-['•'] before:absolute before:-left-3 before:text-teal-500 before:font-bold [ol_&]:before:content-none [ol_&]:list-item">
              {children}
            </li>
          ),
          code: ({ children, className }) => {
            const isBlock = className?.includes("language-");
            if (isBlock) {
              return (
                <code className="block bg-stone-100 rounded-md px-3 py-2 text-[11px] font-mono text-stone-700 my-2 overflow-x-auto whitespace-pre">
                  {children}
                </code>
              );
            }
            return (
              <code className="bg-stone-100 rounded px-1 py-0.5 text-[11px] font-mono text-teal-700">
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="my-2 rounded-md overflow-hidden">{children}</pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-teal-400 pl-3 my-2 text-stone-500 italic">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-3 border-stone-200" />,
          a: ({ href, children }) => (
            <a href={href} className="text-teal-600 underline underline-offset-2 hover:text-teal-700" target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-2">
              <table className="text-[12px] border-collapse w-full">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-stone-200 bg-stone-100 px-2 py-1 text-left font-semibold text-stone-700">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-stone-200 px-2 py-1 text-stone-600">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span className="inline-block w-[3px] h-[13px] bg-teal-500 ml-0.5 align-middle animate-pulse rounded-full" />
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
            className={`rounded-xl px-3.5 py-2.5
              ${isUser
                ? "bg-stone-800 text-stone-100 text-[13px] leading-relaxed"
                : "bg-white border border-stone-200 shadow-sm"
              }`}
          >
            {isUser ? (
              <span>{displayContent}</span>
            ) : displayContent ? (
              <MarkdownContent content={displayContent} isStreaming={message.isStreaming} />
            ) : (
              <span className="text-stone-400 text-xs">Thinking...</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
