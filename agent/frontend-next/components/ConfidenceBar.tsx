"use client";

import { useState, useEffect } from "react";

interface ConfidenceBarProps {
  score: number; // 0.0 to 1.0
}

export default function ConfidenceBar({ score }: ConfidenceBarProps) {
  const [mounted, setMounted] = useState(false);
  const pct = Math.round(score * 100);
  const color =
    score >= 0.8
      ? "bg-accent"
      : score >= 0.6
        ? "bg-warning"
        : "bg-error";

  useEffect(() => {
    // Trigger after first render so the bar animates from 0 → target width
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <div className="mt-3 flex items-center gap-2">
      <span className="shrink-0 text-[12px] font-medium text-text-secondary">
        Confidence: {score.toFixed(2)}
      </span>
      <div
        role="meter"
        aria-label="Confidence score"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 flex-1 rounded-full bg-border"
      >
        <div
          className={`h-2 rounded-full ${color}`}
          style={{
            width: mounted ? `${pct}%` : "0%",
            transition: "width 500ms ease-out",
          }}
        />
      </div>
    </div>
  );
}
