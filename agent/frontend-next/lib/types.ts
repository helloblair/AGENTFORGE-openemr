export interface ChatRequest {
  message: string;
  thread_id: string;
}

export interface ChatResponse {
  response: string;
  thread_id: string;
  tools_used: string[];
  trace_id: string;
  confidence_score: number;
  requires_escalation: boolean;
}

export interface FeedbackRequest {
  trace_id: string;
  score: number; // 0 or 1
  comment?: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  tools_used?: string[];
  confidence_score?: number;
  trace_id?: string;
  requires_escalation?: boolean;
  feedback?: "up" | "down" | null;
}
