import type { ReactNode } from "react";

/** Page title block with an optional subtitle and a single primary action on the right. */
export function PageHeader({
  title,
  subtitle,
  eyebrow,
  actions,
}: {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-wider text-brand">{eyebrow}</p>}
        <h1 className="mt-1 text-2xl font-bold text-navy">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

type Tone = "neutral" | "primary" | "info" | "success" | "warning" | "danger" | "violet";

const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-muted/10 text-muted",
  primary: "bg-brand/10 text-brand",
  info: "bg-cyan/10 text-[#0b8db3]",
  success: "bg-success/10 text-[#12874f]",
  warning: "bg-warning/15 text-[#b9770e]",
  danger: "bg-danger/10 text-danger",
  violet: "bg-violet/10 text-violet",
};

/** Content workflow statuses → semantic tones (Draft neutral · Review warning · Published success · …). */
const STATUS_TONES: Record<string, Tone> = {
  DRAFT: "neutral",
  REVIEW: "warning",
  PUBLISHED: "success",
  SCHEDULED: "info",
  EXPIRED: "danger",
  ARCHIVED: "neutral",
  SENT: "success",
  CANCELLED: "neutral",
  PENDING: "warning",
  REVIEWED: "success",
  IGNORED: "neutral",
  REJECTED: "danger",
  VERIFIED: "success",
  UNVERIFIED: "neutral",
  FAILING: "danger",
  ACTIVE: "success",
  INACTIVE: "neutral",
};

function humanize(value: string) {
  const words = value.replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Status pill — always text, colored by semantic tone. */
export function StatusBadge({ status, tone, label }: { status: string; tone?: Tone; label?: string }) {
  const resolved = tone ?? STATUS_TONES[status] ?? "neutral";
  return (
    <span className={`badge ${TONE_CLASSES[resolved]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" aria-hidden />
      {label ?? humanize(status)}
    </span>
  );
}

/** Filter pill used in table toolbars. */
export function FilterPill({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
        active ? "bg-brand text-white shadow-sm" : "bg-white text-muted shadow-sm hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
