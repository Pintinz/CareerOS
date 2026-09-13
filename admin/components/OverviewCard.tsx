import type { ReactNode } from "react";

type Tone = "primary" | "success" | "warning" | "danger" | "violet" | "info";

const TONES: Record<Tone, string> = {
  primary: "bg-brand/10 text-brand",
  success: "bg-success/10 text-success",
  warning: "bg-warning/15 text-[#b9770e]",
  danger: "bg-danger/10 text-danger",
  violet: "bg-violet/10 text-violet",
  info: "bg-cyan/10 text-[#0b8db3]",
};

interface OverviewCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  tone?: Tone;
}

/** Compact analytics tile — real counts only (no invented deltas). */
export function OverviewCard({ label, value, icon, tone = "primary" }: OverviewCardProps) {
  return (
    <div className="flex items-center gap-4 rounded-2xl bg-card p-5 shadow-sm">
      {icon && <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${TONES[tone]}`}>{icon}</span>}
      <div className="min-w-0">
        <p className="text-2xl font-bold text-navy">{value}</p>
        <p className="truncate text-sm text-muted">{label}</p>
      </div>
    </div>
  );
}
