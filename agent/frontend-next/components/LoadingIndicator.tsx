export default function LoadingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl bg-neutral-100 px-4 py-3 dark:bg-neutral-800">
        {/* Role indicator matching MessageBubble */}
        <div className="mb-1 text-[11px] font-medium text-neutral-400 dark:text-neutral-500">
          Agent
        </div>

        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:0ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:150ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-neutral-400 [animation-delay:300ms]" />
          </div>
          <span className="text-xs text-neutral-400 dark:text-neutral-500">
            Thinking&hellip;
          </span>
        </div>
      </div>
    </div>
  );
}
