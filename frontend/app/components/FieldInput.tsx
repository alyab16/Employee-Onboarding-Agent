"use client";

import { useState, type ReactNode } from "react";

/**
 * Smart field renderer for the HITL approval card.
 *
 * Given a tool argument `name` and its current `value`, we pick an input type
 * that matches the semantic of the field (phone → tel, module_id → dropdown,
 * channels → chip input, etc.) and render it with a matching icon and helper.
 * The component stays uncontrolled on the parent's behalf: it emits typed
 * values (string, string[], etc.) to `onChange` and the parent diffs them
 * against the original args to decide what to send as `edited_args`.
 */

export type FieldValue = string | string[] | number | boolean | null | undefined;

interface Props {
  name: string;
  value: FieldValue | unknown;
  onChange: (next: FieldValue) => void;
  disabled?: boolean;
  edited?: boolean;
}

/** Humanize snake_case → "Snake Case". */
function humanize(name: string): string {
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ---------- curated option lists ---------- */

const TRAINING_MODULES: { id: string; label: string; mins: number }[] = [
  { id: "T1", label: "Company Policies & Code of Conduct", mins: 30 },
  { id: "T2", label: "Security Awareness", mins: 45 },
  { id: "T3", label: "Data Privacy & Compliance", mins: 30 },
  { id: "T4", label: "Role-Specific Onboarding", mins: 60 },
];

const SALES_PERMISSION_SETS = [
  "Sales_Standard",
  "Sales_Manager",
  "Sales_Power_User",
  "Marketing_Analytics",
  "Service_Cloud_Agent",
];

const SLACK_CHANNEL_SUGGESTIONS = [
  "#general",
  "#random",
  "#onboarding",
  "#engineering",
  "#design",
  "#product",
  "#sales",
  "#marketing",
  "#it-help",
  "#announcements",
];

const IT_SYSTEM_SUGGESTIONS = [
  "GitHub",
  "AWS",
  "Jira",
  "Confluence",
  "Datadog",
  "PagerDuty",
  "Salesforce",
  "1Password",
  "Figma",
  "Slack",
  "HubSpot",
  "Tableau",
];

/* ---------- detection ---------- */

type FieldKind =
  | "phone"
  | "email"
  | "location"
  | "name"
  | "title"
  | "module"
  | "permission_set"
  | "channels"
  | "systems"
  | "emoji"
  | "status"
  | "id"
  | "text";

function detect(name: string, value: unknown): FieldKind {
  const n = name.toLowerCase();
  if (Array.isArray(value)) {
    if (n.includes("channel")) return "channels";
    if (n.includes("system")) return "systems";
    return "channels"; // fallback chip-style for any array
  }
  if (n === "module_id" || n === "module") return "module";
  if (n === "permission_set") return "permission_set";
  if (n.includes("phone")) return "phone";
  if (n.includes("email")) return "email";
  if (n.includes("emoji")) return "emoji";
  if (n === "status_text") return "status";
  if (n.includes("location") || n.includes("city") || n === "address")
    return "location";
  if (n.includes("name")) return "name";
  if (n === "title" || n.includes("role") || n === "department") return "title";
  if (n === "employee_id" || n === "id" || n.endsWith("_id")) return "id";
  return "text";
}

/* ---------- icons ---------- */

function Icon({ kind }: { kind: FieldKind }) {
  const common = "w-3.5 h-3.5";
  switch (kind) {
    case "phone":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 0 1 2-2h2.3a1 1 0 0 1 1 .76l1 4a1 1 0 0 1-.5 1.1L7 10a12 12 0 0 0 7 7l1.14-1.8a1 1 0 0 1 1.1-.5l4 1a1 1 0 0 1 .76 1V19a2 2 0 0 1-2 2A16 16 0 0 1 3 5Z" />
        </svg>
      );
    case "email":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path strokeLinecap="round" strokeLinejoin="round" d="m3 7 9 6 9-6" />
        </svg>
      );
    case "location":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 22s8-7.5 8-13a8 8 0 1 0-16 0c0 5.5 8 13 8 13Z" />
          <circle cx="12" cy="9" r="2.5" />
        </svg>
      );
    case "name":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="8" r="4" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 21a8 8 0 0 1 16 0" />
        </svg>
      );
    case "title":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <rect x="3" y="7" width="18" height="13" rx="2" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" />
        </svg>
      );
    case "module":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h10" />
        </svg>
      );
    case "permission_set":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3 4 6v6a8 8 0 0 0 8 8 8 8 0 0 0 8-8V6l-8-3Z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="m9 12 2 2 4-4" />
        </svg>
      );
    case "channels":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 9h10M7 15h10M11 3 9 21M15 3l-2 18" />
        </svg>
      );
    case "systems":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <rect x="3" y="4" width="18" height="6" rx="1" />
          <rect x="3" y="14" width="18" height="6" rx="1" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 17h.01" />
        </svg>
      );
    case "emoji":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="9" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 14a4 4 0 0 0 8 0M9 9h.01M15 9h.01" />
        </svg>
      );
    case "status":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="9" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 7v5l3 2" />
        </svg>
      );
    case "id":
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 10h4M7 14h10" />
        </svg>
      );
    default:
      return (
        <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h10M4 18h16" />
        </svg>
      );
  }
}

/* ---------- text-ish input wrapper ---------- */

function InputShell({
  icon,
  edited,
  disabled,
  children,
  helper,
}: {
  icon: ReactNode;
  edited: boolean;
  disabled?: boolean;
  children: ReactNode;
  helper?: string;
}) {
  return (
    <div className="w-full">
      <div
        className={`flex items-center gap-2 rounded-lg border bg-white px-2.5 py-1.5 transition-all
          ${edited
            ? "border-amber-400 ring-2 ring-amber-200/70"
            : "border-stone-200 focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-100"
          } ${disabled ? "opacity-60" : ""}`}
      >
        <span className={`flex-shrink-0 ${edited ? "text-amber-500" : "text-stone-400"}`}>
          {icon}
        </span>
        {children}
      </div>
      {helper && (
        <p className="mt-1 text-[10px] text-stone-400 pl-0.5">{helper}</p>
      )}
    </div>
  );
}

/* ---------- chip / tag input for array fields ---------- */

function ChipInput({
  values,
  suggestions,
  onChange,
  disabled,
  edited,
  placeholder,
}: {
  values: string[];
  suggestions: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
  edited: boolean;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");

  const add = (raw: string) => {
    const val = raw.trim();
    if (!val) return;
    if (values.includes(val)) {
      setDraft("");
      return;
    }
    onChange([...values, val]);
    setDraft("");
  };

  const remove = (v: string) => {
    onChange(values.filter((x) => x !== v));
  };

  const remaining = suggestions.filter((s) => !values.includes(s));

  return (
    <div className="space-y-1.5 w-full">
      <div
        className={`min-h-[34px] rounded-lg border bg-white px-2 py-1.5 flex flex-wrap items-center gap-1.5 transition-all
          ${edited
            ? "border-amber-400 ring-2 ring-amber-200/70"
            : "border-stone-200 focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-100"
          } ${disabled ? "opacity-60" : ""}`}
      >
        {values.map((v) => (
          <span
            key={v}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-teal-50 text-teal-700 border border-teal-200 text-[11px] font-medium"
          >
            {v}
            {!disabled && (
              <button
                onClick={() => remove(v)}
                className="text-teal-500 hover:text-teal-700 font-bold text-[13px] leading-none"
                aria-label={`Remove ${v}`}
              >
                ×
              </button>
            )}
          </span>
        ))}
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              add(draft);
            } else if (e.key === "Backspace" && draft === "" && values.length) {
              remove(values[values.length - 1]);
            }
          }}
          placeholder={values.length === 0 ? placeholder : ""}
          disabled={disabled}
          className="flex-1 min-w-[80px] bg-transparent outline-none text-[12px] text-stone-800 placeholder-stone-400 py-0.5"
        />
      </div>
      {remaining.length > 0 && !disabled && (
        <div className="flex flex-wrap gap-1 pl-0.5">
          <span className="text-[10px] text-stone-400 mr-1 py-0.5">Suggestions:</span>
          {remaining.slice(0, 6).map((s) => (
            <button
              key={s}
              onClick={() => add(s)}
              className="text-[10px] px-1.5 py-0.5 rounded-md border border-stone-200 bg-white text-stone-500 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- main ---------- */

export function FieldInput({ name, value, onChange, disabled, edited = false }: Props) {
  const kind = detect(name, value);
  const label = humanize(name);

  // Arrays (channels / systems) — chip input
  if (kind === "channels" || kind === "systems") {
    const vals = Array.isArray(value) ? (value as unknown[]).map(String) : [];
    const suggestions =
      kind === "channels" ? SLACK_CHANNEL_SUGGESTIONS : IT_SYSTEM_SUGGESTIONS;
    return (
      <FieldRow label={label} edited={edited}>
        <ChipInput
          values={vals}
          suggestions={suggestions}
          onChange={onChange}
          disabled={disabled}
          edited={edited}
          placeholder={
            kind === "channels"
              ? "Type a channel and hit enter..."
              : "Type a system and hit enter..."
          }
        />
      </FieldRow>
    );
  }

  // Training module — read-only. Modules must be completed in order (T1 → T4)
  // and the backend enforces this, so letting the user re-pick the module from
  // a dropdown is misleading: it implies they can mark T4 done while on T1.
  // If the agent picked the wrong module, the right path is Reject + reply.
  if (kind === "module") {
    const current = String(value ?? "").toUpperCase();
    const meta = TRAINING_MODULES.find((m) => m.id === current);
    return (
      <FieldRow label={label} edited={false}>
        <div className="flex-1 flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-stone-50 border border-stone-200">
          <Icon kind="module" />
          <span className="text-[12px] font-mono text-stone-700">{current}</span>
          {meta && (
            <span className="text-[12px] text-stone-500 truncate">
              — {meta.label} ({meta.mins} min)
            </span>
          )}
          <span className="ml-auto text-[9px] uppercase tracking-wider text-stone-400 flex-shrink-0">
            read-only
          </span>
        </div>
      </FieldRow>
    );
  }

  // Permission set dropdown
  if (kind === "permission_set") {
    const current = String(value ?? "");
    const options = SALES_PERMISSION_SETS.includes(current)
      ? SALES_PERMISSION_SETS
      : current
      ? [current, ...SALES_PERMISSION_SETS]
      : SALES_PERMISSION_SETS;
    return (
      <FieldRow label={label} edited={edited}>
        <InputShell icon={<Icon kind="permission_set" />} edited={edited} disabled={disabled}>
          <select
            value={current}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className="flex-1 bg-transparent outline-none text-[12px] text-stone-800 py-0.5 font-mono"
          >
            <option value="" disabled>
              Pick a permission set...
            </option>
            {options.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </InputShell>
      </FieldRow>
    );
  }

  // Employee id — show as read-only pill
  if (kind === "id") {
    return (
      <FieldRow label={label} edited={false}>
        <div className="flex-1 flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-stone-50 border border-stone-200">
          <Icon kind="id" />
          <span className="text-[12px] font-mono text-stone-500">{String(value)}</span>
          <span className="ml-auto text-[9px] uppercase tracking-wider text-stone-400">
            read-only
          </span>
        </div>
      </FieldRow>
    );
  }

  // Phone / email / location / name / title / status / emoji / text
  const inputType =
    kind === "phone" ? "tel" : kind === "email" ? "email" : "text";
  const placeholder =
    kind === "phone"
      ? "e.g. 415-555-0100"
      : kind === "email"
      ? "e.g. jane@acme.com"
      : kind === "location"
      ? "City, State or Country"
      : kind === "emoji"
      ? "e.g. :rocket:"
      : kind === "status"
      ? "What's your status?"
      : kind === "name"
      ? "Full name"
      : kind === "title"
      ? "Your title"
      : `Enter ${label.toLowerCase()}`;
  const helper =
    kind === "phone"
      ? "Any common format works (we'll normalize)."
      : kind === "email"
      ? "Personal email — not your company address."
      : undefined;

  return (
    <FieldRow label={label} edited={edited}>
      <InputShell
        icon={<Icon kind={kind} />}
        edited={edited}
        disabled={disabled}
        helper={helper}
      >
        <input
          type={inputType}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder={placeholder}
          className="flex-1 bg-transparent outline-none text-[12px] text-stone-800 placeholder-stone-400 py-0.5"
        />
      </InputShell>
    </FieldRow>
  );
}

function FieldRow({
  label,
  edited,
  children,
}: {
  label: string;
  edited: boolean;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-stone-500">
          {label}
        </span>
        {edited && (
          <span className="text-[9px] uppercase tracking-wider text-amber-600 font-semibold px-1.5 py-0.5 bg-amber-50 rounded">
            edited
          </span>
        )}
      </div>
      {children}
    </div>
  );
}
