"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { Message } from "@/lib/types";
import ToolCallsPanel from "./ToolCallsPanel";
import ConfidenceBar from "./ConfidenceBar";
import EscalationWarning from "./EscalationWarning";
import FeedbackButtons from "./FeedbackButtons";

// ── Markdown component overrides ─────────────────────────────────────────────

const markdownComponents: Components = {
  code({ className, children, ...rest }) {
    const isInline = !className;
    if (isInline) {
      return (
        <code
          className="rounded bg-neutral-200 px-1 py-0.5 font-mono text-[13px] dark:bg-neutral-700"
          {...rest}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        className={`block overflow-x-auto rounded-lg bg-neutral-900 p-3 font-mono text-[13px] leading-relaxed text-neutral-100 dark:bg-neutral-950 ${className ?? ""}`}
        {...rest}
      >
        {children}
      </code>
    );
  },
  pre({ children }) {
    return <pre className="my-2">{children}</pre>;
  },
  p({ children }) {
    return <p className="mb-2 last:mb-0">{children}</p>;
  },
  ul({ children }) {
    return <ul className="mb-2 ml-4 list-disc last:mb-0">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="mb-2 ml-4 list-decimal last:mb-0">{children}</ol>;
  },
  li({ children }) {
    return <li className="mb-0.5">{children}</li>;
  },
  strong({ children }) {
    return <strong className="font-semibold">{children}</strong>;
  },
};

// ── MessageBubble ────────────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: Message;
  onFeedback?: (traceId: string, score: "up" | "down") => void;
}

export default function MessageBubble({
  message,
  onFeedback,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100"
        }`}
      >
        {/* Role indicator */}
        <div
          className={`mb-1 text-[11px] font-medium ${
            isUser
              ? "text-blue-200"
              : "text-neutral-400 dark:text-neutral-500"
          }`}
        >
          {isUser ? "You" : "Agent"}
        </div>

        {/* Content */}
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <div className="prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Assistant-only metadata */}
        {!isUser && (
          <>
            {message.tools_used && message.tools_used.length > 0 && (
              <ToolCallsPanel tools={message.tools_used} />
            )}

            {message.confidence_score != null && (
              <ConfidenceBar score={message.confidence_score} />
            )}

            {message.requires_escalation && <EscalationWarning />}

            {message.trace_id && (
              <FeedbackButtons
                traceId={message.trace_id}
                currentFeedback={message.feedback ?? null}
                onFeedback={onFeedback ?? (() => {})}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
