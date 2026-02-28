"use client";

import { useState } from "react";

// ── Tool icon SVGs ───────────────────────────────────────────────────────────

function PatientIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path d="M10 8a3 3 0 100-6 3 3 0 000 6zM3.465 14.493a1.23 1.23 0 00.41 1.412A9.957 9.957 0 0010 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 00-13.074.003z" />
    </svg>
  );
}

function AllergyIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path fillRule="evenodd" d="M10.339 2.237a.532.532 0 00-.678 0 11.947 11.947 0 01-7.078 2.75.5.5 0 00-.479.425A12.11 12.11 0 002 7c0 5.163 3.26 9.564 7.834 11.257a.48.48 0 00.332 0C14.74 16.564 18 12.163 18 7c0-.538-.035-1.069-.104-1.589a.5.5 0 00-.48-.425 11.947 11.947 0 01-7.077-2.75zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
    </svg>
  );
}

function MedicationIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path d="M11.983 1.907a.75.75 0 00-1.292-.657l-8.5 9.5A.75.75 0 002.75 12h6.572l-1.305 6.093a.75.75 0 001.292.657l8.5-9.5A.75.75 0 0017.25 8h-6.572l1.305-6.093z" />
    </svg>
  );
}

function ProblemListIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path fillRule="evenodd" d="M15.988 3.012A2.25 2.25 0 0118 5.25v6.5A2.25 2.25 0 0115.75 14H13.5v-3.379a3 3 0 00-.879-2.121l-3.12-3.121a3 3 0 00-1.402-.791 2.252 2.252 0 011.913-1.576A2.25 2.25 0 0112.25 1h1.5a2.25 2.25 0 012.238 2.012zM11.5 3.25a.75.75 0 01.75-.75h1.5a.75.75 0 01.75.75v.25a.75.75 0 01-.75.75h-1.5a.75.75 0 01-.75-.75v-.25z" clipRule="evenodd" />
      <path d="M3.5 6A1.5 1.5 0 002 7.5v9A1.5 1.5 0 003.5 18h7a1.5 1.5 0 001.5-1.5v-5.879a1.5 1.5 0 00-.44-1.06L8.44 6.439A1.5 1.5 0 007.378 6H3.5z" />
    </svg>
  );
}

function ProviderIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path d="M10 .5a9.5 9.5 0 105.598 17.177C14.466 15.177 12.383 13.5 10 13.5s-4.466 1.677-5.598 4.177A9.5 9.5 0 0010 .5zM3.5 10a6.5 6.5 0 0113 0 6.5 6.5 0 01-13 0z" />
      <path d="M10 5a3 3 0 100 6 3 3 0 000-6z" />
    </svg>
  );
}

function InsuranceIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path fillRule="evenodd" d="M1 6a3 3 0 013-3h12a3 3 0 013 3v8a3 3 0 01-3 3H4a3 3 0 01-3-3V6zm4 1.5a2 2 0 114 0 2 2 0 01-4 0zm2 3a4 4 0 00-3.665 2.395.75.75 0 00.416 1A8.98 8.98 0 007 14.5a8.98 8.98 0 003.249-.604.75.75 0 00.416-1.001A4.001 4.001 0 007 10.5zm6-1a.75.75 0 01.75-.75h2a.75.75 0 010 1.5h-2a.75.75 0 01-.75-.75zm.75 2.25a.75.75 0 000 1.5h2a.75.75 0 000-1.5h-2z" clipRule="evenodd" />
    </svg>
  );
}

function DrugInteractionIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
    </svg>
  );
}

// ── Tool metadata ────────────────────────────────────────────────────────────

interface ToolMeta {
  icon: () => React.ReactNode;
  borderColor: string;
}

const TOOL_META: Record<string, ToolMeta> = {
  patient_lookup: {
    icon: PatientIcon,
    borderColor: "border-l-[#1E3A5F]",       // primary blue
  },
  allergy_check: {
    icon: AllergyIcon,
    borderColor: "border-l-[#EF4444]",        // red/warning
  },
  medication_list: {
    icon: MedicationIcon,
    borderColor: "border-l-[#10B981]",         // emerald
  },
  problem_list: {
    icon: ProblemListIcon,
    borderColor: "border-l-[#F59E0B]",         // amber
  },
  provider_lookup: {
    icon: ProviderIcon,
    borderColor: "border-l-[#6366F1]",         // indigo
  },
  insurance_coverage: {
    icon: InsuranceIcon,
    borderColor: "border-l-[#8B5CF6]",         // violet
  },
  drug_interaction_check: {
    icon: DrugInteractionIcon,
    borderColor: "border-l-[#F97316]",         // orange
  },
};

const DEFAULT_META: ToolMeta = {
  icon: () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5 shrink-0">
      <path fillRule="evenodd" d="M13.5 4.938a7 7 0 11-9.006 1.737c.28-.042.553-.112.82-.195a.75.75 0 00-.44-1.435 6.973 6.973 0 01-1.234.262A6.985 6.985 0 013 7.5c0 2.071.9 3.932 2.33 5.212l.457-.456a.75.75 0 011.06 1.06l-.457.457A6.978 6.978 0 0010 14.5c1.573 0 3.024-.52 4.192-1.395l-.357-.357a.75.75 0 011.06-1.06l.357.357A6.978 6.978 0 0016.5 7.5c0-1.573-.52-3.024-1.395-4.193l-1.09 1.09A4.478 4.478 0 0115 7.5a4.5 4.5 0 11-6.654-3.95.75.75 0 10-.692-1.333A6.003 6.003 0 004 7.5a6 6 0 1012.595-1.37.75.75 0 10-1.347.66A4.478 4.478 0 0115 7.5a4.478 4.478 0 01-.57 2.182l1.09-1.09A6.978 6.978 0 0017 7.5a7 7 0 00-3.5-6.062z" clipRule="evenodd" />
    </svg>
  ),
  borderColor: "border-l-[#94A3B8]",
};

function getToolMeta(tool: string): ToolMeta {
  return TOOL_META[tool] ?? DEFAULT_META;
}

// ── Component ────────────────────────────────────────────────────────────────

interface ToolCallsPanelProps {
  tools: string[];
}

export default function ToolCallsPanel({ tools }: ToolCallsPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex cursor-pointer select-none items-center gap-1.5 text-[12px] font-medium text-text-secondary hover:text-text-primary transition-colors"
      >
        {/* Chevron rotates when open */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-3.5 w-3.5 shrink-0 transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}
        >
          <path
            fillRule="evenodd"
            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
            clipRule="evenodd"
          />
        </svg>
        Tools called ({tools.length})
      </button>

      <div
        className="tool-panel-content"
        data-open={isOpen}
      >
        <div>
          <div className="mt-2 flex flex-wrap gap-1.5 pl-0 sm:pl-5">
            {tools.map((tool) => {
              const meta = getToolMeta(tool);
              const Icon = meta.icon;
              return (
                <span
                  key={tool}
                  className={`inline-flex items-center gap-1 rounded-md border-l-2 sm:gap-1.5 ${meta.borderColor} bg-secondary px-2 py-1 font-mono text-[10px] text-primary shadow-sm transition-shadow duration-150 hover:shadow-md sm:px-2.5 sm:text-[11px]`}
                >
                  <Icon />
                  {tool}
                </span>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
