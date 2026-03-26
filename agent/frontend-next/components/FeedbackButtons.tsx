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
    <div className="mt-2 flex items-center gap-1.5 px-1">
      <span className="text-[10px] font-bold uppercase text-text-muted">
        {voted ? "Thanks for your feedback!" : "Was this helpful?"}
      </span>

      {/* Thumbs up */}
      <button
        type="button"
        aria-label="Helpful response"
        aria-pressed={currentFeedback === "up"}
        disabled={voted}
        onClick={() => handleVote("up")}
        className={`rounded p-1 transition-colors ${
          currentFeedback === "up"
            ? "text-accent cursor-default"
            : voted
              ? "text-text-muted cursor-default"
              : "text-text-muted hover:text-accent"
        }`}
      >
        <span className="text-base leading-none">👍</span>
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
            ? "text-error cursor-default"
            : voted
              ? "text-text-muted cursor-default"
              : "text-text-muted hover:text-error"
        }`}
      >
        <span className="text-base leading-none">👎</span>
      </button>
    </div>
  );
}
