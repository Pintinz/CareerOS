"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { OverviewCard } from "@/components/OverviewCard";
import { api, ApiError } from "@/lib/apiClient";
import { getBackendHealth, HealthStatus } from "@/lib/api";

interface DashboardData {
  users: number;
  published_jobs: number;
  published_scholarships: number;
  companies: number;
  intelligence_posts: number;
  aptitude_questions: number;
  interview_questions: number;
  applications_tracked: number;
  content_status: Record<string, Record<string, number>>;
  gmail_connections: number;
  outlook_connections: number;
  connections_requiring_reauth: number;
  failed_email_syncs: number;
  discovery_items_awaiting_review: number;
}

export default function DashboardPage() {
  const { checked } = useAdminGuard();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    getBackendHealth().then(setHealth);
    api
      .get<DashboardData>("/admin/dashboard")
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load dashboard data."));
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

      {error && <p className="mb-6 text-sm text-danger">{error}</p>}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <OverviewCard label="Users" value={data.users} />
            <OverviewCard label="Published Jobs" value={data.published_jobs} />
            <OverviewCard label="Published Scholarships" value={data.published_scholarships} />
            <OverviewCard label="Companies" value={data.companies} />
            <OverviewCard label="Intelligence Posts" value={data.intelligence_posts} />
            <OverviewCard label="Aptitude Questions" value={data.aptitude_questions} />
            <OverviewCard label="Interview Questions" value={data.interview_questions} />
            <OverviewCard label="Applications Tracked" value={data.applications_tracked} />
          </div>

          <h2 className="mb-3 mt-10 text-lg font-semibold text-navy">Email Tracking Operations</h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <OverviewCard label="Gmail Connections" value={data.gmail_connections} />
            <OverviewCard label="Outlook Connections" value={data.outlook_connections} />
            <OverviewCard label="Reauth Required" value={data.connections_requiring_reauth} />
            <OverviewCard label="Failed Syncs" value={data.failed_email_syncs} />
            <OverviewCard label="Discovery Awaiting Review" value={data.discovery_items_awaiting_review} />
          </div>

          <h2 className="mb-3 mt-10 text-lg font-semibold text-navy">Content Status</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {Object.entries(data.content_status).map(([entity, breakdown]) => (
              <div key={entity} className="rounded-2xl bg-card p-6 shadow-sm">
                <p className="mb-2 text-sm font-medium capitalize text-ink">{entity}</p>
                {Object.entries(breakdown).map(([status, count]) => (
                  <div key={status} className="flex justify-between text-sm text-muted">
                    <span>{status}</span>
                    <span className="font-medium text-ink">{count}</span>
                  </div>
                ))}
                {Object.keys(breakdown).length === 0 && <p className="text-sm text-muted">No content yet.</p>}
              </div>
            ))}
          </div>
        </>
      )}
    </main>
  );
}
