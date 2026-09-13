"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { OverviewCard } from "@/components/OverviewCard";
import { ApiError, api } from "@/lib/apiClient";

interface ProviderStatus {
  status: "HEALTHY" | "DISABLED";
  detail: string;
}

interface JobRun {
  last_run_at: string;
  duration_seconds: number;
  success: boolean;
  result: number | null;
  error: string | null;
}

interface OperationsData {
  email_tracking: {
    active_gmail_connections: number;
    active_outlook_connections: number;
    reauthorization_required: number;
    sync_errors: number;
    gmail_provider_status: ProviderStatus;
    outlook_provider_status: ProviderStatus;
  };
  content_ingestion: {
    active_sources: number;
    failed_sources: number;
    discovered_today: number;
    awaiting_review: number;
  };
  background_jobs: Record<string, JobRun>;
}

function StatusBadge({ status }: { status: ProviderStatus["status"] }) {
  const color = status === "HEALTHY" ? "bg-success/10 text-success" : "bg-muted/10 text-muted";
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{status}</span>;
}

export default function OperationsPage() {
  const { checked } = useAdminGuard();
  const [data, setData] = useState<OperationsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    api
      .get<OperationsData>("/admin/dashboard/operations")
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load operations data."));
  }, [checked]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-navy">Operations</h1>
      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      {data && (
        <>
          <h2 className="mb-3 mt-8 text-lg font-semibold text-navy">Email Tracking</h2>
          <div className="mb-3 flex gap-4">
            <div className="flex items-center gap-2 rounded-2xl bg-card px-4 py-3 shadow-sm">
              <span className="text-sm">Gmail</span>
              <StatusBadge status={data.email_tracking.gmail_provider_status.status} />
            </div>
            <div className="flex items-center gap-2 rounded-2xl bg-card px-4 py-3 shadow-sm">
              <span className="text-sm">Outlook</span>
              <StatusBadge status={data.email_tracking.outlook_provider_status.status} />
            </div>
          </div>
          <p className="mb-4 text-xs text-muted">
            {data.email_tracking.gmail_provider_status.detail} · {data.email_tracking.outlook_provider_status.detail}
          </p>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <OverviewCard label="Active Gmail Connections" value={data.email_tracking.active_gmail_connections} />
            <OverviewCard label="Active Outlook Connections" value={data.email_tracking.active_outlook_connections} />
            <OverviewCard label="Reauthorization Required" value={data.email_tracking.reauthorization_required} />
            <OverviewCard label="Sync Errors" value={data.email_tracking.sync_errors} />
          </div>

          <h2 className="mb-3 mt-8 text-lg font-semibold text-navy">Content Ingestion</h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <OverviewCard label="Active Sources" value={data.content_ingestion.active_sources} />
            <OverviewCard label="Failed Sources" value={data.content_ingestion.failed_sources} />
            <OverviewCard label="Discovered Today" value={data.content_ingestion.discovered_today} />
            <OverviewCard label="Awaiting Review" value={data.content_ingestion.awaiting_review} />
          </div>

          <h2 className="mb-3 mt-8 text-lg font-semibold text-navy">Background Jobs</h2>
          <div className="overflow-x-auto rounded-2xl bg-card shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-black/5 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-3">Job</th>
                  <th className="px-4 py-3">Last Run</th>
                  <th className="px-4 py-3">Success</th>
                  <th className="px-4 py-3">Duration (s)</th>
                  <th className="px-4 py-3">Error</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(data.background_jobs).length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-muted">
                      No jobs have run yet in this backend process.
                    </td>
                  </tr>
                )}
                {Object.entries(data.background_jobs).map(([name, run]) => (
                  <tr key={name} className="border-b border-black/5 last:border-0">
                    <td className="px-4 py-3 font-medium">{name}</td>
                    <td className="px-4 py-3 text-muted">{new Date(run.last_run_at).toLocaleString()}</td>
                    <td className={`px-4 py-3 ${run.success ? "text-success" : "text-danger"}`}>{run.success ? "Yes" : "No"}</td>
                    <td className="px-4 py-3 text-muted">{run.duration_seconds.toFixed(2)}</td>
                    <td className="px-4 py-3 text-danger">{run.error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
