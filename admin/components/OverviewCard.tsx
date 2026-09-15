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

const HINT_TONES: Record<Tone, string> = {
  primary: "text-muted",
  success: "text-[#12874f]",
  warning: "text-[#b9770e]",
  danger: "text-danger",
  violet: "text-muted",
  info: "text-muted",
};

interface OverviewCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  tone?: Tone;
  /** Short truthful descriptor under the value ("Needs attention", "All clear"). Never an invented delta. */
  hint?: string;
}

/** Analytics tile: label, large value, optional descriptor, icon top-right — real counts only. */
export function OverviewCard({ label, value, icon, tone = "primary", hint }: OverviewCardProps) {
  const formatted = typeof value === "number" ? value.toLocaleString() : value;
  // Long text values (a date, "12 · 4") step down so they never wrap inside a tile.
  const valueSize = String(formatted).length > 9 ? "text-lg" : "text-[28px]";
  return (
    <div className="flex min-h-[112px] flex-col justify-between rounded-2xl bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium leading-snug text-muted">{label}</p>
        {icon && (
          <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl [&>svg]:h-[18px] [&>svg]:w-[18px] ${TONES[tone]}`}>
            {icon}
          </span>
        )}
      </div>
      <div className="mt-3">
        <p className={`${valueSize} font-bold leading-none tracking-tight text-navy tabular-nums`}>{formatted}</p>
        {hint && <p className={`mt-1.5 text-xs font-medium ${HINT_TONES[tone]}`}>{hint}</p>}
      </div>
    </div>
  );
}

/** Section title for admin dashboards: calm title plus a one-line description. */
export function SectionTitle({ id, title, description }: { id: string; title: string; description?: string }) {
  return (
    <div className="mb-4">
      <h2 id={id} className="text-base font-semibold text-navy">
        {title}
      </h2>
      {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
    </div>
  );
}
