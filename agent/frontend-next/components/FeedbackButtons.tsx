"use client";

import { toast } from "sonner";

interface FeedbackButtonsProps {
  traceId: string;
  currentFeedback: "up" | "down" | null;
  onFeedback: (traceId: string, score: "up" | "down") => void;
}

export default function FeedbackButtons({
  traceId,
  currentFeedback,
  onFeedback,
}: FeedbackButtonsProps) {
  const voted = currentFeedback !== null;

  function handleVote(score: "up" | "down") {
    onFeedback(traceId, score);
    toast.success("Feedback recorded — thank you!");
  }

  return (
    <div className="mt-2 flex items-center gap-1">
      {/* Thumbs up */}
      <button
        type="button"
        aria-label="Helpful response"
        aria-pressed={currentFeedback === "up"}
        disabled={voted}
        onClick={() => handleVote("up")}
        className={`rounded p-1 transition-colors ${
          currentFeedback === "up"
            ? "text-emerald-500 cursor-default"
            : voted
              ? "text-text-muted cursor-default"
              : "text-text-muted hover:text-emerald-500"
        }`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill={currentFeedback === "up" ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth={1.5}
          className="h-5 w-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M7 11V4a2 2 0 0 1 2-2h.5a.5.5 0 0 1 .5.5V6l2-1 2.5 4H11v5a2 2 0 0 1-2 2H7.5A1.5 1.5 0 0 1 6 15.5V11ZM4 11H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1Z"
          />
        </svg>
      </button>

      {/* Thumbs down */}
      <button
        type="button"
        aria-label="Unhelpful response"
        aria-pressed={currentFeedback === "down"}
        disabled={voted}
        onClick={() => handleVote("down")}
        className={`rounded p-1 transition-colors ${
          currentFeedback === "down"
            ? "text-red-500 cursor-default"
            : voted
              ? "text-text-muted cursor-default"
              : "text-text-muted hover:text-red-500"
        }`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill={currentFeedback === "down" ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth={1.5}
          className="h-5 w-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13 9v7a2 2 0 0 1-2 2h-.5a.5.5 0 0 1-.5-.5V14l-2 1-2.5-4H9V6a2 2 0 0 1 2-2h1.5A1.5 1.5 0 0 1 14 5.5V9ZM16 9h1a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-5a1 1 0 0 1 1-1Z"
          />
        </svg>
      </button>
    </div>
  );
}
