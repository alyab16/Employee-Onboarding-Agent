"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message, PendingApproval, ToolActivity } from "../types";
import {
  SERVER_COLORS,
  SERVER_LABELS,
  SPECIALIST_COLORS,
} from "../types";

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

interface ApprovalCardProps {
  approval: PendingApproval;
  onApprove: (editedArgs?: Record<string, unknown>) => void;
  onReject: (reason?: string) => void;
  disabled: boolean;
}

/** Shallow equality for scalar edited-arg values. */
function sameValue(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a === "string" && typeof b === "string") return a === b;
  return JSON.stringify(a) === JSON.stringify(b);
}

function ApprovalCard({ approval, onApprove, onReject, disabled }: ApprovalCardProps) {
  const colors = SERVER_COLORS[approval.server] ?? SERVER_COLORS.unknown;
  const serverLabel = SERVER_LABELS[approval.server] ?? approval.server;
  const argEntries = Object.entries(approval.args).filter(
    ([, v]) => v !== "" && v != null,
  );

  // Local edits to string-valued args. Keys only appear here once the user
  // actually typed something — we diff against `approval.args` on submit so we
  // only send fields that changed.
  const [edits, setEdits] = useState<Record<string, string>>({});

  if (approval.status === "approved") {
    return (
      <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-[11px] text-emerald-700 flex items-center gap-2">
        <span>✓</span>
        <span className="font-medium">Approved:</span>
        <span className="font-mono text-emerald-800">{approval.tool}</span>
        <span className="ml-auto text-emerald-500">{approval.action}</span>
      </div>
    );
  }

  if (approval.status === "rejected") {
    return (
      <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700 flex items-center gap-2">
        <span>✗</span>
        <span className="font-medium">Rejected:</span>
        <span className="font-mono text-rose-800">{approval.tool}</span>
        <span className="ml-auto text-rose-500">
          {approval.reason?.trim() ? approval.reason : approval.action}
        </span>
      </div>
    );
  }

  const diffEdits = Object.entries(edits).reduce<Record<string, unknown>>(
    (acc, [k, v]) => {
      if (!sameValue(v, approval.args[k])) acc[k] = v;
      return acc;
    },
    {},
  );
  const hasEdits = Object.keys(diffEdits).length > 0;

  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 p-3 space-y-2 shadow-sm">
      <div className="flex items-center gap-2 text-[11px]">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        <span className="font-semibold text-amber-900 uppercase tracking-wider text-[10px]">
          Approval required
        </span>
        <span
          className={`ml-auto px-1.5 py-0.5 rounded text-[10px] font-medium ${colors.bg} ${colors.text}`}
        >
          {serverLabel}
        </span>
      </div>
      <p className="text-[13px] text-stone-800 font-medium leading-snug">
        {approval.action}
      </p>
      <p className="text-[11px] font-mono text-stone-500">{approval.tool}</p>
      {argEntries.length > 0 && (
        <div className="rounded bg-white/70 border border-amber-200 px-2 py-1.5 space-y-1">
          {argEntries.map(([k, v]) => {
            const isEditable = typeof v === "string";
            const displayValue = isEditable
              ? (edits[k] ?? (v as string))
              : JSON.stringify(v);
            const isEdited = isEditable && k in diffEdits;
            return (
              <div key={k} className="flex gap-2 text-[11px] items-center">
                <span className="font-mono text-stone-400 flex-shrink-0 min-w-[5rem]">
                  {k}
                </span>
                {isEditable ? (
                  <input
                    type="text"
                    value={displayValue}
                    onChange={(e) =>
                      setEdits((prev) => ({ ...prev, [k]: e.target.value }))
                    }
                    disabled={disabled}
                    className={`flex-1 bg-white rounded px-1.5 py-0.5 text-stone-800 outline-none border transition-colors ${
                      isEdited
                        ? "border-amber-400 ring-1 ring-amber-300"
                        : "border-stone-200 focus:border-amber-400"
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  />
                ) : (
                  <span className="text-stone-700 break-all">{displayValue}</span>
                )}
                {isEdited && (
                  <span className="text-[9px] uppercase tracking-wider text-amber-600 font-semibold flex-shrink-0">
                    edited
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
      {hasEdits && (
        <p className="text-[10px] text-amber-700 leading-snug">
          {Object.keys(diffEdits).length} field{Object.keys(diffEdits).length > 1 ? "s" : ""} edited — the agent will use your values.
        </p>
      )}
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onApprove(hasEdits ? diffEdits : undefined)}
          disabled={disabled}
          className="flex-1 text-[12px] font-medium px-3 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {hasEdits ? "Approve with edits" : "Approve"}
        </button>
        <button
          onClick={() => onReject()}
          disabled={disabled}
          className="flex-1 text-[12px] font-medium px-3 py-1.5 rounded-md bg-white border border-stone-300 text-stone-700 hover:bg-stone-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Reject
        </button>
      </div>
    </div>
  );
}

function HandoffBadges({ handoffs }: { handoffs: { specialist: string; label: string }[] }) {
  if (!handoffs || handoffs.length === 0) return null;
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {handoffs.map((h, i) => {
        const colors = SPECIALIST_COLORS[h.specialist];
        return (
          <span
            key={`${h.specialist}-${i}`}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
              colors
                ? `${colors.bg} ${colors.text} ${colors.border}`
                : "bg-stone-50 text-stone-600 border-stone-200"
            }`}
          >
            <span className="w-1 h-1 rounded-full bg-current opacity-60" />
            {h.label}
          </span>
        );
      })}
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
  onApprove?: (editedArgs?: Record<string, unknown>) => void;
  onReject?: (reason?: string) => void;
  isBusy?: boolean;
}

export function MessageBubble({ message, onApprove, onReject, isBusy }: Props) {
  const isUser = message.role === "user";
  const displayContent = safeString(message.content);
  const approvals = message.approvals ?? [];
  const pendingApproval = approvals.find((a) => a.status === "pending");

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
        {/* Specialist handoff badges */}
        {!isUser && message.handoffs && message.handoffs.length > 0 && (
          <HandoffBadges handoffs={message.handoffs} />
        )}

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

        {/* Approval cards */}
        {!isUser && approvals.length > 0 && (
          <div className="w-full space-y-1.5">
            {approvals.map((approval, i) => (
              <ApprovalCard
                key={approval.interruptId ?? `${approval.tool}-${i}`}
                approval={approval}
                onApprove={(editedArgs) => onApprove?.(editedArgs)}
                onReject={(reason) => onReject?.(reason)}
                disabled={
                  !!isBusy ||
                  approval.status !== "pending" ||
                  approval !== pendingApproval
                }
              />
            ))}
          </div>
        )}

        {/* Message text */}
        {(displayContent || message.isStreaming || message.awaitingApproval) && (
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
            ) : message.awaitingApproval ? (
              <span className="text-amber-600 text-xs">Paused — awaiting your approval above.</span>
            ) : (
              <span className="text-stone-400 text-xs">Thinking...</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
