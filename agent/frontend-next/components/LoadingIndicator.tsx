export default function LoadingIndicator() {
  return (
    <div className="flex justify-start animate-message-in-left">
      <div className="max-w-[80%] rounded-2xl bg-surface-secondary px-4 py-3">
        {/* Role indicator matching MessageBubble */}
        <div className="mb-1 text-[11px] font-medium text-text-muted">
          Veris
        </div>

        {/* Skeleton lines mimicking a response */}
        <div className="flex flex-col gap-2">
          <div className="h-3 w-52 rounded bg-border animate-skeleton-pulse" />
          <div className="h-3 w-40 rounded bg-border animate-skeleton-pulse [animation-delay:200ms]" />
          <div className="h-3 w-48 rounded bg-border animate-skeleton-pulse [animation-delay:400ms]" />
        </div>

        {/* Subtle status text */}
        <div className="mt-3 text-xs text-text-muted">
          Agent is thinking&hellip;
        </div>
      </div>
    </div>
  );
}
