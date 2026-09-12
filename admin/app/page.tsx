"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { OverviewCard } from "@/components/OverviewCard";
import { getBackendHealth, HealthStatus } from "@/lib/api";

// Phase 2: overview counts aren't wired to real aggregate endpoints yet (no admin "stats"
// route exists). Showing "—" rather than a fabricated number until that endpoint exists.
const OVERVIEW_CARDS = [
  "Active Users",
  "Jobs Published",
  "Scholarships",
  "News Articles",
  "Applications Tracked",
  "Questions",
];

export default function DashboardPage() {
  const { checked } = useAdminGuard();
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    if (checked) getBackendHealth().then(setHealth);
  }, [checked]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-8">
        <p className="text-sm font-medium text-brand">CareerOS Admin</p>
        <h1 className="mt-1 text-2xl font-semibold text-navy">Dashboard</h1>
      </header>

      <div
        className={`mb-8 flex items-center gap-2 rounded-xl px-4 py-3 text-sm ${
          health ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
        }`}
      >
        <span className={`h-2 w-2 rounded-full ${health ? "bg-success" : "bg-danger"}`} />
        {health
          ? `Backend connected — ${health.service} v${health.version} (${health.environment})`
          : "Backend unreachable — start the FastAPI server (see README) before publishing content."}
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {OVERVIEW_CARDS.map((label) => (
          <OverviewCard key={label} label={label} value="—" />
        ))}
      </div>

      <p className="mt-8 text-sm text-muted">
        Companies and Jobs are live in the nav above. News, Scholarships, and the Question Bank
        land in later phases — see <code>PROJECT_STATUS.md</code>.
      </p>
    </main>
  );
}
