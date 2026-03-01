"use client";

export default function EscalationWarning() {
  return (
    <div role="alert" className="mt-3 flex items-start gap-2 rounded-md border border-error/30 bg-error/10 px-3 py-2 text-[12px] font-medium leading-snug text-error">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="mt-0.5 h-4 w-4 shrink-0"
      >
        <path
          fillRule="evenodd"
          d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.345 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z"
          clipRule="evenodd"
        />
      </svg>
      <span>
        Low confidence — please verify this information with a qualified
        healthcare professional before making clinical decisions.
      </span>
    </div>
  );
}
