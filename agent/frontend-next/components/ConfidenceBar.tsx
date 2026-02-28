"use client";

interface ConfidenceBarProps {
  score: number; // 0.0 to 1.0
}

export default function ConfidenceBar({ score }: ConfidenceBarProps) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.8
      ? "bg-emerald-500"
      : score >= 0.6
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div className="mt-3 flex items-center gap-2">
      <span className="shrink-0 text-[12px] font-medium text-neutral-500 dark:text-neutral-400">
        Confidence: {score.toFixed(2)}
      </span>
      <div className="h-2 flex-1 rounded-full bg-neutral-200 dark:bg-neutral-700">
        <div
          className={`h-2 rounded-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
