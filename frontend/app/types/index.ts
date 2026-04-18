export interface Employee {
  id: string;
  name: string;
  role: string;
  level: string;
  department: string;
  email: string;
}

/** SSE event types streamed from the backend */
export type AgentEventType =
  | "text_delta"
  | "tool_call"
  | "tool_result"
  | "agent_handoff"
  | "approval_required"
  | "awaiting_approval"
  | "done"
  | "error";

export interface TextDeltaEvent {
  type: "text_delta";
  content: string;
}

export interface ToolCallEvent {
  type: "tool_call";
  tool: string;
  server: string;
  input: Record<string, unknown>;
}

export interface ToolResultEvent {
  type: "tool_result";
  tool: string;
  output: string;
}

export interface AgentHandoffEvent {
  type: "agent_handoff";
  specialist: string;
  label: string;
}

export interface ApprovalRequiredEvent {
  type: "approval_required";
  interrupt_id: string | null;
  kind: "tool_approval";
  tool: string;
  server: string;
  action: string;
  args: Record<string, unknown>;
}

export interface AwaitingApprovalEvent {
  type: "awaiting_approval";
}

export interface DoneEvent {
  type: "done";
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export type AgentEvent =
  | TextDeltaEvent
  | ToolCallEvent
  | ToolResultEvent
  | AgentHandoffEvent
  | ApprovalRequiredEvent
  | AwaitingApprovalEvent
  | DoneEvent
  | ErrorEvent;

/** A single message in the chat UI */
export type MessageRole = "user" | "assistant" | "tool";

export interface ToolActivity {
  tool: string;
  server: string;
  input: Record<string, unknown>;
  output?: string;
}

export interface SpecialistHandoff {
  specialist: string;
  label: string;
}

export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface PendingApproval {
  interruptId: string | null;
  tool: string;
  server: string;
  action: string;
  args: Record<string, unknown>;
  status: ApprovalStatus;
  reason?: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  /** Tool calls that happened while generating this assistant message */
  toolActivities?: ToolActivity[];
  /** Specialists that handled this message, in the order they ran */
  handoffs?: SpecialistHandoff[];
  /** Approval cards rendered inside this message (current + resolved) */
  approvals?: PendingApproval[];
  isStreaming?: boolean;
  /** Is this message currently paused waiting for human approval? */
  awaitingApproval?: boolean;
}

/** MCP server styling */
export const SERVER_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  hr:         { bg: "bg-orange-50", text: "text-orange-600", dot: "bg-orange-400" },
  slack:      { bg: "bg-fuchsia-50", text: "text-fuchsia-600", dot: "bg-fuchsia-400" },
  salesforce: { bg: "bg-sky-50", text: "text-sky-600", dot: "bg-sky-400" },
  training:   { bg: "bg-lime-50", text: "text-lime-600", dot: "bg-lime-500" },
  it:         { bg: "bg-teal-50", text: "text-teal-600", dot: "bg-teal-400" },
  knowledge:  { bg: "bg-violet-50", text: "text-violet-600", dot: "bg-violet-400" },
  unknown:    { bg: "bg-stone-50", text: "text-stone-500", dot: "bg-stone-400" },
};

export const SERVER_LABELS: Record<string, string> = {
  hr: "HR Platform",
  slack: "Slack",
  salesforce: "Salesforce",
  training: "Training Platform",
  it: "IT Ticketing",
  knowledge: "Knowledge Base",
  unknown: "Unknown",
};

export const SPECIALIST_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  hr_profile: { bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
  training:   { bg: "bg-lime-50",   text: "text-lime-700",   border: "border-lime-200"   },
  it_access:  { bg: "bg-teal-50",   text: "text-teal-700",   border: "border-teal-200"   },
  knowledge:  { bg: "bg-violet-50", text: "text-violet-700", border: "border-violet-200" },
};
