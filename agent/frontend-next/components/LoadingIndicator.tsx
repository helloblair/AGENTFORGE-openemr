export default function LoadingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl bg-surface-secondary px-4 py-3">
        {/* Role indicator matching MessageBubble */}
        <div className="mb-1 text-[11px] font-medium text-text-muted">
          Veris
        </div>

        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <span className="h-2 w-2 animate-bounce rounded-full bg-text-muted [animation-delay:0ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-text-muted [animation-delay:150ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-text-muted [animation-delay:300ms]" />
          </div>
          <span className="text-xs text-text-muted">
            Thinking&hellip;
          </span>
        </div>
      </div>
    </div>
  );
}
