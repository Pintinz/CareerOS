interface OverviewCardProps {
  label: string;
  value: string | number;
}

export function OverviewCard({ label, value }: OverviewCardProps) {
  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
    </div>
  );
}
