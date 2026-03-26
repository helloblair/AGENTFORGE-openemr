interface ClinicalDisclaimerProps {
  disclaimers: string[];
}

export default function ClinicalDisclaimer({ disclaimers }: ClinicalDisclaimerProps) {
  if (disclaimers.length === 0) return null;

  return (
    <div className="mt-2 rounded-lg border border-border/40 bg-surface-secondary/60 px-3 py-2">
      <p className="mb-1 font-mono text-[9px] font-bold uppercase tracking-wider text-text-muted">
        Disclaimer:
      </p>
      <p className="mb-1 font-mono text-[10px] font-bold uppercase leading-snug text-text-muted">
        This is not medical advice.
      </p>
      <ul className="list-disc pl-4 space-y-0.5">
        <li className="font-mono text-[10px] font-bold uppercase leading-snug text-text-muted">
          This information is for clinical support only.
        </li>
        <li className="font-mono text-[10px] font-bold uppercase leading-snug text-text-muted">
          Please verify with your healthcare provider before making any clinical decisions.
        </li>
      </ul>
    </div>
  );
}
