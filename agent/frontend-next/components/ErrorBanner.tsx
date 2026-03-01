interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export default function ErrorBanner({
  message,
  onRetry,
  onDismiss,
}: ErrorBannerProps) {
  return (
    <div role="alert" className="flex items-center gap-3 border-t border-error/30 bg-error/10 px-4 py-2.5">
      {/* Error icon */}
      <svg
        className="h-4 w-4 shrink-0 text-error"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z"
          clipRule="evenodd"
        />
      </svg>

      {/* Message */}
      <span className="flex-1 text-sm text-error">
        {message}
      </span>

      {/* Retry button */}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded px-2.5 py-1 text-xs font-medium text-error transition-colors hover:bg-error/20"
        >
          Retry
        </button>
      )}

      {/* Dismiss button */}
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="rounded p-1 text-error transition-colors hover:bg-error/20"
        >
          <svg
            className="h-4 w-4"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      )}
    </div>
  );
}
