"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import {
  IconBriefcase,
  IconBuilding,
  IconGraduation,
  IconInsights,
  IconMail,
  IconMic,
  IconQuiz,
  IconSearch,
  IconShield,
  IconUsers,
  IconPulse,
} from "@/components/icons";
import { OverviewCard } from "@/components/OverviewCard";
import { PageHeader, StatusBadge } from "@/components/ui";
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
  const [healthChecked, setHealthChecked] = useState(false);
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    getBackendHealth().then((h) => {
      setHealth(h);
      setHealthChecked(true);
    });
    api
      .get<DashboardData>("/admin/dashboard")
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load dashboard data."));
  }, [checked]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-8 py-10">
      <PageHeader eyebrow="CareerOS Admin" title="Dashboard" subtitle="Content, question banks and platform operations at a glance." />

      {healthChecked && (
        <div
          role="status"
          className={`mb-8 flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium shadow-sm ${
            health ? "bg-white text-ink" : "bg-danger/5 text-danger"
          }`}
        >
          <span className={`h-2.5 w-2.5 rounded-full ${health ? "bg-success" : "bg-danger"}`} aria-hidden />
          {health
            ? `Backend connected — ${health.service} v${health.version} (${health.environment})`
            : "Backend unreachable — start the FastAPI server (see README) before publishing content."}
        </div>
      )}

      {error && <p className="mb-6 rounded-xl bg-danger/5 px-4 py-3 text-sm text-danger">{error}</p>}

      {!data && !error && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4" aria-label="Loading">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-[84px] animate-pulse rounded-2xl bg-white shadow-sm" />
          ))}
        </div>
      )}

      {data && (
        <>
          <section aria-labelledby="platform">
            <h2 id="platform" className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">
              Platform
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <OverviewCard label="Users" value={data.users} icon={<IconUsers />} />
              <OverviewCard label="Applications tracked" value={data.applications_tracked} icon={<IconPulse />} tone="success" />
              <OverviewCard label="Published jobs" value={data.published_jobs} icon={<IconBriefcase />} />
              <OverviewCard label="Published scholarships" value={data.published_scholarships} icon={<IconGraduation />} tone="violet" />
              <OverviewCard label="Companies" value={data.companies} icon={<IconBuilding />} tone="info" />
              <OverviewCard label="Intelligence posts" value={data.intelligence_posts} icon={<IconInsights />} tone="info" />
              <OverviewCard label="Aptitude questions" value={data.aptitude_questions} icon={<IconQuiz />} tone="violet" />
              <OverviewCard label="Interview questions" value={data.interview_questions} icon={<IconMic />} tone="warning" />
            </div>
          </section>

          <section aria-labelledby="operations" className="mt-10">
            <h2 id="operations" className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">
              Email tracking & discovery
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <OverviewCard label="Gmail connections" value={data.gmail_connections} icon={<IconMail />} />
              <OverviewCard label="Outlook connections" value={data.outlook_connections} icon={<IconMail />} />
              <OverviewCard
                label="Reauth required"
                value={data.connections_requiring_reauth}
                icon={<IconShield />}
                tone={data.connections_requiring_reauth > 0 ? "warning" : "success"}
              />
              <OverviewCard
                label="Failed syncs"
                value={data.failed_email_syncs}
                icon={<IconPulse />}
                tone={data.failed_email_syncs > 0 ? "danger" : "success"}
              />
              <OverviewCard label="Awaiting review" value={data.discovery_items_awaiting_review} icon={<IconSearch />} tone="warning" />
            </div>
          </section>

          <section aria-labelledby="content-status" className="mt-10">
            <h2 id="content-status" className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">
              Content status
            </h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {Object.entries(data.content_status).map(([entity, breakdown]) => (
                <div key={entity} className="rounded-2xl bg-card p-5 shadow-sm">
                  <p className="mb-3 text-sm font-semibold capitalize text-navy">{entity}</p>
                  <ul className="space-y-2">
                    {Object.entries(breakdown).map(([status, count]) => (
                      <li key={status} className="flex items-center justify-between text-sm">
                        <StatusBadge status={status} />
                        <span className="font-semibold tabular-nums text-ink">{count}</span>
                      </li>
                    ))}
                  </ul>
                  {Object.keys(breakdown).length === 0 && <p className="text-sm text-muted">No content yet.</p>}
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
