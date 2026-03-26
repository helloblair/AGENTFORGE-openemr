"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { Message } from "@/lib/types";
import ConfidenceBar from "./ConfidenceBar";
import EscalationWarning from "./EscalationWarning";
import FeedbackButtons from "./FeedbackButtons";
import ClinicalDisclaimer from "./ClinicalDisclaimer";
import CopyButton from "./CopyButton";

// ── Tool pill color map (matches ToolCallsPanel palette) ─────────────────────

const TOOL_PILL_STYLES: Record<string, string> = {
  patient_lookup:        "border-primary/30 bg-primary/10 text-primary",
  allergy_check:         "border-error/30 bg-error/10 text-error",
  medication_list:       "border-accent/30 bg-accent/10 text-accent",
  problem_list:          "border-warning/30 bg-warning/10 text-warning",
  provider_lookup:       "border-primary/30 bg-primary/10 text-primary",
  insurance_coverage:    "border-accent/30 bg-accent/10 text-accent",
  drug_interaction_check:"border-warning/30 bg-warning/10 text-warning",
  lab_results:           "border-primary/30 bg-primary/10 text-primary",
  transplant_criteria_lookup: "border-accent/30 bg-accent/10 text-accent",
  transplant_screening:  "border-error/30 bg-error/10 text-error",
};

const TOOL_NAMES = new Set(Object.keys(TOOL_PILL_STYLES));

function isToolName(text: string): boolean {
  return TOOL_NAMES.has(text.trim());
}

function ToolPill({ name }: { name: string }) {
  const style = TOOL_PILL_STYLES[name] ?? "border-text-muted/30 bg-text-muted/10 text-text-secondary";
  return (
    <span className={`inline-flex items-center rounded-md border px-1.5 py-0.5 font-mono text-[11px] font-medium ${style}`}>
      {name}
    </span>
  );
}

// ── Disclaimer / body splitter ───────────────────────────────────────────────
// Backend appends disclaimers after "---" separators. Split them out so we can
// render the main content in a card and disclaimers as small muted text below.

const DISCLAIMER_SEPARATOR = /\n{2,}---\n/;

function splitDisclaimers(content: string): { body: string; disclaimers: string[] } {
  const parts = content.split(DISCLAIMER_SEPARATOR);
  const body = parts[0];
  const disclaimers = parts.slice(1).map((d) => d.replace(/^---$/, "").trim()).filter(Boolean);
  return { body, disclaimers };
}

// ── Markdown component overrides ─────────────────────────────────────────────

const markdownComponents: Components = {
  code({ className, children, ...rest }) {
    const isInline = !className;
    if (isInline) {
      const text = typeof children === "string" ? children : String(children ?? "");
      if (isToolName(text)) {
        return <ToolPill name={text.trim()} />;
      }
      return (
        <code
          className="rounded bg-secondary px-1 py-0.5 font-mono text-[13px]"
          {...rest}
        >
          {children}
        </code>
      );
    }
    return (
      <code
        className={`block overflow-x-auto rounded-lg bg-primary p-3 font-mono text-[13px] leading-relaxed text-white ${className ?? ""}`}
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
  table({ children }) {
    return (
      <div className="my-2 overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">{children}</table>
      </div>
    );
  },
  th({ children }) {
    return (
      <th className="border-b border-border px-2 py-1.5 text-left text-[12px] font-semibold text-text-secondary">
        {children}
      </th>
    );
  },
  td({ children }) {
    return (
      <td className="border-b border-border/50 px-2 py-1.5">{children}</td>
    );
  },
};

// ── Inline tools row ─────────────────────────────────────────────────────────

function ToolsCalledRow({ tools }: { tools: string[] }) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5">
      <span className="text-[11px] font-medium text-text-secondary">Tools called:</span>
      {tools.map((tool) => (
        <ToolPill key={tool} name={tool} />
      ))}
    </div>
  );
}

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
  const { body, disclaimers: rawDisclaimers } = isUser
    ? { body: message.content, disclaimers: [] }
    : splitDisclaimers(message.content);
  // Filter out duplicate confidence lines already rendered by ConfidenceBar
  const disclaimers = rawDisclaimers.filter((d) => !/^\*{0,2}Confidence[:\s]/i.test(d));

  if (isUser) {
    return (
      <div className="flex justify-end animate-message-in-right">
        <div className="max-w-[85%] rounded-2xl bg-primary px-4 py-3 text-sm leading-relaxed text-white sm:max-w-[75%] md:max-w-[70%]">
          <div className="mb-1 text-[10px] font-medium text-white/60 sm:text-[11px]">
            You
          </div>
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start animate-message-in-left">
      <div className="group max-w-full sm:max-w-[85%] md:max-w-[80%]">
        {/* Role indicator */}
        <div className="mb-1.5 text-[10px] font-bold uppercase text-text-muted sm:text-[11px]">
          Veris
        </div>

        {/* Main response card */}
        <div className="relative rounded-xl border border-border/60 bg-white px-5 py-4 text-sm leading-relaxed text-text-primary shadow-sm dark:bg-surface">
          <CopyButton text={message.content} />

          <div className="prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {body}
            </ReactMarkdown>
          </div>

          {/* Tools called — inline pills */}
          {message.tools_used && message.tools_used.length > 0 && (
            <ToolsCalledRow tools={message.tools_used} />
          )}

          {/* Confidence bar */}
          {message.confidence_score != null && (
            <ConfidenceBar score={message.confidence_score} />
          )}
        </div>

        {/* Escalation warning — outside card for prominence */}
        {message.requires_escalation && (
          <div className="mt-2">
            <EscalationWarning />
          </div>
        )}

        {/* Disclaimers — attached to this message */}
        <ClinicalDisclaimer disclaimers={disclaimers} />

        {/* Feedback — at the very bottom with label */}
        {message.trace_id && (
          <FeedbackButtons
            traceId={message.trace_id}
            currentFeedback={message.feedback ?? null}
            onFeedback={onFeedback ?? (() => {})}
          />
        )}
      </div>
    </div>
  );
}
