import { OverviewCard } from "@/components/OverviewCard";
import { getBackendHealth } from "@/lib/api";

// Phase 0: overview counts are not wired to real tables yet (no domain models exist).
// Showing "—" rather than a fabricated number until Phase 9 admin content endpoints exist.
const OVERVIEW_CARDS = [
  "Active Users",
  "Jobs Published",
  "Scholarships",
  "News Articles",
  "Applications Tracked",
  "Questions",
];

export default async function DashboardPage() {
  const health = await getBackendHealth();

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
        Content review queues, publishing tools, question bank, and source registry land in
        Phase 9 — see <code>PROJECT_STATUS.md</code>.
      </p>
    </main>
  );
}
