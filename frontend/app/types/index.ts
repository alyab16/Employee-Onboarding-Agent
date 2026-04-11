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

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  /** Tool calls that happened while generating this assistant message */
  toolActivities?: ToolActivity[];
  isStreaming?: boolean;
}

/** MCP server styling */
export const SERVER_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  hr:         { bg: "bg-orange-50", text: "text-orange-600", dot: "bg-orange-400" },
  slack:      { bg: "bg-fuchsia-50", text: "text-fuchsia-600", dot: "bg-fuchsia-400" },
  salesforce: { bg: "bg-sky-50", text: "text-sky-600", dot: "bg-sky-400" },
  training:   { bg: "bg-lime-50", text: "text-lime-600", dot: "bg-lime-500" },
  it:         { bg: "bg-teal-50", text: "text-teal-600", dot: "bg-teal-400" },
  unknown:    { bg: "bg-stone-50", text: "text-stone-500", dot: "bg-stone-400" },
};

export const SERVER_LABELS: Record<string, string> = {
  hr: "HR Platform",
  slack: "Slack",
  salesforce: "Salesforce",
  training: "Training Platform",
  it: "IT Ticketing",
  unknown: "Unknown",
};
