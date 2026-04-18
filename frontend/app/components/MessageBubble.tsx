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
import { FieldInput, type FieldValue } from "./FieldInput";

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

/** Split args into fields the user can usefully edit vs. hidden context. */
function partitionArgs(args: Record<string, unknown>) {
  const hidden: Record<string, unknown> = {};
  const visible: [string, unknown][] = [];
  for (const [k, v] of Object.entries(args)) {
    if (v === "" || v == null) continue;
    // Hide employee_id from the form — it's context, not something to edit.
    if (k === "employee_id") {
      hidden[k] = v;
      continue;
    }
    visible.push([k, v]);
  }
  return { hidden, visible };
}

function ApprovalCard({ approval, onApprove, onReject, disabled }: ApprovalCardProps) {
  const colors = SERVER_COLORS[approval.server] ?? SERVER_COLORS.unknown;
  const serverLabel = SERVER_LABELS[approval.server] ?? approval.server;
  const { hidden, visible } = partitionArgs(approval.args);

  // Local edits — can be string, string[], or other scalar types. We diff
  // against `approval.args` on submit so only changed fields are sent.
  const [edits, setEdits] = useState<Record<string, FieldValue>>({});
  const [showDetails, setShowDetails] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  if (approval.status === "approved") {
    return (
      <div className="rounded-lg border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50 px-3.5 py-2.5 text-[11px] flex items-center gap-2.5 shadow-sm animate-fade-in-up">
        <span className="w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">
          ✓
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-emerald-800 text-[12px]">Approved</p>
          <p className="text-emerald-600 truncate">{approval.action}</p>
        </div>
        <span className="font-mono text-[10px] text-emerald-600/70 flex-shrink-0">
          {approval.tool}
        </span>
      </div>
    );
  }

  if (approval.status === "rejected") {
    return (
      <div className="rounded-lg border border-rose-200 bg-gradient-to-br from-rose-50 to-pink-50 px-3.5 py-2.5 text-[11px] flex items-center gap-2.5 shadow-sm animate-fade-in-up">
        <span className="w-5 h-5 rounded-full bg-rose-500 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">
          ✗
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-rose-800 text-[12px]">Rejected</p>
          <p className="text-rose-600 truncate">
            {approval.reason?.trim() ? approval.reason : approval.action}
          </p>
        </div>
        <span className="font-mono text-[10px] text-rose-600/70 flex-shrink-0">
          {approval.tool}
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
  const editedCount = Object.keys(diffEdits).length;

  const handleApprove = () => {
    onApprove(hasEdits ? diffEdits : undefined);
  };

  return (
    <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 via-white to-orange-50 p-4 space-y-3 shadow-md animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2 flex-shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
        </span>
        <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-amber-800">
          Review &amp; Approve
        </span>
        <span
          className={`ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${colors.bg} ${colors.text} border border-current/10`}
        >
          <span className={`w-1 h-1 rounded-full ${colors.dot}`} />
          {serverLabel}
        </span>
      </div>

      {/* Action title */}
      <div>
        <p className="text-[14px] font-semibold text-stone-900 leading-tight">
          {approval.action}
        </p>
        <p className="text-[10px] font-mono text-stone-400 mt-0.5">
          {approval.tool}
        </p>
      </div>

      {/* Form body */}
      {visible.length > 0 && (
        <div className="space-y-3 rounded-lg bg-white/80 border border-amber-200/60 p-3 backdrop-blur-sm">
          {visible.map(([k, v]) => {
            const currentVal = k in edits ? edits[k] : (v as FieldValue);
            const isEdited = k in diffEdits;
            return (
              <FieldInput
                key={k}
                name={k}
                value={currentVal}
                onChange={(next) =>
                  setEdits((prev) => ({ ...prev, [k]: next }))
                }
                disabled={disabled}
                edited={isEdited}
              />
            );
          })}
        </div>
      )}

      {/* Hidden context (employee_id, etc.) — collapsible */}
      {Object.keys(hidden).length > 0 && (
        <div>
          <button
            onClick={() => setShowDetails((v) => !v)}
            className="text-[10px] text-stone-400 hover:text-stone-600 flex items-center gap-1 transition-colors"
          >
            <svg
              className={`w-2.5 h-2.5 transition-transform ${showDetails ? "rotate-90" : ""}`}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
            Context
          </button>
          {showDetails && (
            <div className="mt-1.5 space-y-0.5 text-[10px] font-mono text-stone-500 pl-4">
              {Object.entries(hidden).map(([k, v]) => (
                <div key={k}>
                  <span className="text-stone-400">{k}:</span>{" "}
                  <span className="text-stone-600">{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Edit summary */}
      {hasEdits && (
        <div className="flex items-center gap-1.5 text-[10px] text-amber-700 bg-amber-100/60 border border-amber-200 rounded-md px-2 py-1">
          <svg className="w-3 h-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
          </svg>
          <span>
            <strong>{editedCount}</strong> field{editedCount > 1 ? "s" : ""} edited — your values will be used instead of the agent&apos;s.
          </span>
        </div>
      )}

      {/* Reject reason drawer */}
      {showReject && (
        <div className="space-y-1.5 rounded-lg bg-white border border-rose-200 p-2.5">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-rose-700">
            Why are you rejecting?
          </label>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Optional — helps the agent adjust its next step."
            disabled={disabled}
            rows={2}
            className="w-full text-[12px] rounded-md border border-stone-200 px-2 py-1.5 outline-none focus:border-rose-400 focus:ring-2 focus:ring-rose-100 resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={() => {
                onReject(rejectReason.trim() || undefined);
                setShowReject(false);
              }}
              disabled={disabled}
              className="flex-1 text-[12px] font-medium px-3 py-1.5 rounded-md bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50 transition-colors"
            >
              Confirm reject
            </button>
            <button
              onClick={() => {
                setShowReject(false);
                setRejectReason("");
              }}
              disabled={disabled}
              className="text-[12px] font-medium px-3 py-1.5 rounded-md bg-white border border-stone-300 text-stone-600 hover:bg-stone-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Actions */}
      {!showReject && (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            disabled={disabled}
            className="flex-1 inline-flex items-center justify-center gap-1.5 text-[13px] font-semibold px-3 py-2 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-sm hover:shadow-md hover:from-emerald-600 hover:to-teal-700 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            {hasEdits ? "Approve with edits" : "Approve"}
          </button>
          <button
            onClick={() => setShowReject(true)}
            disabled={disabled}
            className="inline-flex items-center justify-center gap-1.5 text-[13px] font-medium px-3 py-2 rounded-lg bg-white border border-stone-300 text-stone-700 hover:bg-stone-50 hover:border-stone-400 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Reject
          </button>
        </div>
      )}
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
    <div
      className={`flex gap-3 animate-fade-in-up ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-[10px] font-bold shadow-sm ring-1
          ${isUser
            ? "bg-gradient-to-br from-stone-700 to-stone-900 text-white ring-stone-900/10"
            : "bg-gradient-to-br from-teal-500 via-teal-600 to-emerald-600 text-white ring-teal-900/20"
          }`}
      >
        {isUser ? "You" : (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2M12 19v2M5 12H3M21 12h-2M6 6l1.5 1.5M16.5 16.5 18 18M6 18l1.5-1.5M16.5 7.5 18 6" />
            <circle cx="12" cy="12" r="4" />
          </svg>
        )}
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
