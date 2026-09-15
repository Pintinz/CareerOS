"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { OverviewCard } from "@/components/OverviewCard";
import { FilterPill, PageHeader, StatusBadge } from "@/components/ui";
import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import {
  CONTENT_TYPE_LABELS,
  ContentChange,
  ContentType,
  DiscoveredItem,
  DiscoveryMetrics,
  ItemStatus,
  SourceHealth,
  formatDate,
  humanize,
} from "@/types/discovery";
import { Company, PaginatedResponse } from "@/types/models";

const TABS: { key: ContentType | "ALL"; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "JOB", label: "Jobs" },
  { key: "SCHOLARSHIP", label: "Scholarships" },
  { key: "INTERNSHIP", label: "Internships" },
  { key: "GRADUATE_PROGRAM", label: "Graduate Programs" },
  { key: "TRAINEE_PROGRAM", label: "Trainee Programmes" },
  { key: "APPRENTICESHIP", label: "Apprenticeships" },
  { key: "FELLOWSHIP", label: "Fellowships" },
  { key: "INTELLIGENCE", label: "Intelligence" },
];

const STATUS_OPTIONS: ItemStatus[] = ["NEEDS_REVIEW", "VERIFIED", "NEW", "DUPLICATE", "DRAFT_CREATED", "PUBLISHED", "SOURCE_REMOVED", "IGNORED", "REJECTED"];
const PAGE_SIZE = 25;

export default function DiscoveryPage() {
  return (
    <Suspense fallback={null}>
      <DiscoveryQueue />
    </Suspense>
  );
}

function DiscoveryQueue() {
  const { checked } = useAdminGuard();
  const params = useSearchParams();
  const [tab, setTab] = useState<ContentType | "ALL">("ALL");
  const [status, setStatus] = useState("");
  const [sourceId, setSourceId] = useState(params.get("source_id") ?? "");
  const [companyId, setCompanyId] = useState("");
  const [country, setCountry] = useState("");
  const [minTrust, setMinTrust] = useState("");
  const [duplicates, setDuplicates] = useState("");
  const [since, setSince] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<PaginatedResponse<DiscoveredItem> | null>(null);
  const [metrics, setMetrics] = useState<DiscoveryMetrics | null>(null);
  const [sources, setSources] = useState<SourceHealth[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (tab !== "ALL") query.set("item_type", tab);
    if (status) query.set("status", status);
    if (sourceId) query.set("source_id", sourceId);
    if (companyId) query.set("company_id", companyId);
    if (country.trim()) query.set("country", country.trim());
    if (minTrust) query.set("min_trust", minTrust);
    if (duplicates) query.set("duplicates", duplicates);
    if (since) query.set("discovered_after", new Date(since).toISOString());
    if (search.trim()) query.set("search", search.trim());
    try {
      const [items, metricData] = await Promise.all([
        api.get<PaginatedResponse<DiscoveredItem>>(`/admin/discovery?${query.toString()}`),
        api.get<DiscoveryMetrics>("/admin/discovery/metrics"),
      ]);
      setData(items);
      setMetrics(metricData);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load the discovery queue.");
    }
  }, [page, tab, status, sourceId, companyId, country, minTrust, duplicates, since, search]);

  useEffect(() => {
    if (!checked) return;
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
  }, [checked, load]);

  useEffect(() => {
    if (!checked) return;
    api.get<SourceHealth[]>("/admin/sources").then(setSources).catch(() => undefined);
    api.get<PaginatedResponse<Company>>("/admin/companies?page=1&page_size=100").then((res) => setCompanies(res.items)).catch(() => undefined);
  }, [checked]);

  useEffect(() => setPage(1), [tab, status, sourceId, companyId, country, minTrust, duplicates, since, search]);

  async function decide(item: DiscoveredItem, action: "ignore" | "reject" | "create-draft") {
    try {
      await api.post(`/admin/discovery/${item.id}/${action}`, action === "create-draft" ? {} : undefined);
      if (action === "create-draft") setNotice(`Draft created for “${item.detected_title}”. Review and publish it from the item page.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed.");
    }
  }

  async function runDue() {
    try {
      const result = await api.post<{ queued: number }>("/admin/discovery/run-due");
      setNotice(result.queued ? `${result.queued} due source(s) queued for discovery.` : "No sources are due yet — use Run discovery on a source to check it now.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to queue discovery.");
    }
  }

  async function verify() {
    try {
      await api.post("/admin/discovery/verify");
      setNotice("Re-verification of published listings has started. Removed or closed listings will appear as pending changes.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start verification.");
    }
  }

  if (!checked) return null;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const sourceName = Object.fromEntries(sources.map((s) => [s.id, s.name]));

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <PageHeader
        eyebrow="Research operations"
        title="Discovery Queue"
        subtitle="Candidates found at registered sources, with the evidence behind each. Review, create a draft or publish — nothing is published by default."
        actions={
          <>
            <button className="btn-secondary" onClick={verify}>Verify active listings</button>
            <button className="btn-primary" onClick={runDue}>Run due sources</button>
          </>
        }
      />

      {metrics && (
        <>
          <section className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <OverviewCard label="Awaiting review" value={metrics.awaiting_review} tone="warning" />
            <OverviewCard label="New · updated (24h)" value={`${metrics.items_new_24h} · ${metrics.items_updated_24h}`} tone="primary" />
            <OverviewCard label="Pending source changes" value={metrics.pending_changes + metrics.source_removed_pending} tone="info" />
            <OverviewCard label="Duplicates (24h)" value={metrics.duplicates_24h} tone="info" />
          </section>
          <section className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <OverviewCard label="Healthy sources" value={`${metrics.healthy_sources} / ${metrics.active_sources}`} tone="success" />
            <OverviewCard label="Failed sources" value={metrics.failing_sources} tone={metrics.failing_sources ? "danger" : "success"} />
            <OverviewCard label="Possibly removed · expired (7d)" value={`${metrics.possibly_removed} · ${metrics.opportunities_expired_7d}`} tone="warning" />
            <OverviewCard label="Last sync" value={metrics.last_run_at ? formatDate(metrics.last_run_at, true) : "—"} tone="info" />
          </section>
          {(metrics.jobs_by_country.length > 0 || metrics.jobs_by_industry.length > 0) && (
            <section className="mb-6 grid gap-4 md:grid-cols-2">
              <Breakdown title="Live jobs by country" rows={metrics.jobs_by_country.map((r) => [r.country, r.count])} />
              <Breakdown title="Live jobs by industry" rows={metrics.jobs_by_industry.map((r) => [r.industry, r.count])} />
            </section>
          )}
        </>
      )}

      <div className="mb-4 flex flex-wrap gap-2" role="tablist" aria-label="Content type">
        {TABS.map((t) => (
          <FilterPill key={t.key} active={tab === t.key} onClick={() => setTab(t.key)}>
            {t.label}
          </FilterPill>
        ))}
      </div>

      <div className="mb-4 grid gap-3 rounded-2xl bg-card p-4 shadow-sm md:grid-cols-4 lg:grid-cols-8">
        <input aria-label="Search titles" placeholder="Search titles" value={search} onChange={(e) => setSearch(e.target.value)} className="lg:col-span-2" />
        <select aria-label="Source" value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <select aria-label="Company" value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
          <option value="">All companies</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <input aria-label="Country" placeholder="Country" value={country} onChange={(e) => setCountry(e.target.value)} />
        <select aria-label="Minimum trust" value={minTrust} onChange={(e) => setMinTrust(e.target.value)}>
          <option value="">Any trust</option>
          {[5, 4, 3, 2].map((level) => (
            <option key={level} value={level}>Trust ≥ {level}</option>
          ))}
        </select>
        <select aria-label="Status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Needs a decision</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{humanize(s)}</option>
          ))}
        </select>
        <select aria-label="Duplicates" value={duplicates} onChange={(e) => setDuplicates(e.target.value)}>
          <option value="">Duplicates: any</option>
          <option value="exclude">Hide duplicates</option>
          <option value="only">Duplicates only</option>
        </select>
        <label className="flex items-center gap-2 text-xs text-muted lg:col-span-2">
          Found since
          <input type="date" value={since} onChange={(e) => setSince(e.target.value)} className="flex-1" />
        </label>
      </div>

      {notice && <p className="mb-4 rounded-xl bg-brand/10 px-4 py-3 text-sm text-brand">{notice}</p>}
      {error && <p className="mb-4 rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>}

      <PendingChanges onChanged={load} onError={setError} />

      <div className="overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full min-w-[1080px] text-left text-sm">
          <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Item</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Dates</th>
              <th className="px-4 py-3">Deadline</th>
              <th className="px-4 py-3">Trust · confidence</th>
              <th className="px-4 py-3">Verification</th>
              <th className="px-4 py-3">Duplicate / update</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-muted">
                  Nothing in this view. New candidates appear here after a source is checked.
                </td>
              </tr>
            )}
            {data?.items.map((item) => (
              <tr key={item.id} className="border-b border-line align-top last:border-0">
                <td className="max-w-sm px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-brand">{CONTENT_TYPE_LABELS[item.item_type]}</p>
                  <Link href={`/discovery/${item.id}`} className="font-semibold text-ink hover:text-brand">
                    {item.detected_title}
                  </Link>
                  <p className="text-xs text-muted">
                    {item.detected_company_name ?? "Organization not matched"}
                    {item.location ? ` · ${item.location}` : ""}
                    {item.country && !(item.location ?? "").includes(item.country) ? ` · ${item.country}` : ""}
                  </p>
                  {item.external_id && (
                    <p className="truncate text-xs text-muted" title={item.external_id}>
                      Job ID {item.external_id}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-muted">
                  <p>{item.source_name ?? sourceName[item.source_id] ?? "—"}</p>
                  {item.source_type && <p className="text-xs">{humanize(item.source_type)}</p>}
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  <p>Posted {formatDate(item.published_at)}</p>
                  <p>Found {formatDate(item.created_at)}</p>
                </td>
                <td className="px-4 py-3 text-muted">{formatDate(item.deadline)}</td>
                <td className="px-4 py-3">
                  <p className="font-semibold text-navy">{item.trust_level ?? "—"}/5</p>
                  <p className="text-xs text-muted">{item.confidence !== null ? `${Math.round(item.confidence * 100)}% extraction confidence` : "—"}</p>
                </td>
                <td className="space-y-1 px-4 py-3">
                  <StatusBadge status={item.status} />
                  <div>
                    <StatusBadge status={item.verification_status} />
                  </div>
                  {item.flags.length > 0 && <p className="text-xs text-danger">{item.flags.map(humanize).join(", ")}</p>}
                </td>
                <td className="px-4 py-3 text-xs text-muted">
                  {item.duplicate_of_id && <p>Duplicate of another source&rsquo;s item</p>}
                  {item.matched_entity_id && <p>Matches an existing {humanize(item.matched_entity_type)} record</p>}
                  {item.pending_changes > 0 && <p className="font-semibold text-[#b9770e]">{item.pending_changes} detected change(s)</p>}
                  {item.missing_runs > 0 && <p className="font-semibold text-[#b9770e]">Missing from source in {item.missing_runs} sync(s)</p>}
                  {!item.duplicate_of_id && !item.matched_entity_id && <p>New</p>}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col items-end gap-2">
                    <Link href={`/discovery/${item.id}`} className="btn-primary px-3 py-1.5 text-xs">Review</Link>
                    <a href={item.canonical_url ?? item.original_url} target="_blank" rel="noreferrer noopener" className="text-xs text-brand">
                      View original
                    </a>
                    {["NEW", "NEEDS_REVIEW", "VERIFIED", "DUPLICATE"].includes(item.status) && (
                      <div className="flex gap-3 text-xs">
                        {item.status !== "DUPLICATE" && (
                          <button onClick={() => decide(item, "create-draft")} className="text-brand">
                            Create draft
                          </button>
                        )}
                        <button onClick={() => decide(item, "ignore")} className="text-muted hover:text-ink">Ignore</button>
                        <button onClick={() => decide(item, "reject")} className="text-danger">Reject</button>
                      </div>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && data.total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm text-muted">
          <span>
            Page {page} of {totalPages} · {data.total} items
          </span>
          <div className="flex gap-2">
            <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
            <button className="btn-secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
          </div>
        </div>
      )}
    </main>
  );
}

const RECORD_ROUTES: Record<string, string> = { JOB: "jobs", SCHOLARSHIP: "scholarships", INTELLIGENCE: "intelligence" };

function Breakdown({ title, rows }: { title: string; rows: [string, number][] }) {
  const max = Math.max(1, ...rows.map(([, n]) => n));
  return (
    <div className="rounded-2xl bg-card p-4 shadow-sm">
      <p className="mb-3 text-sm font-semibold text-navy">{title}</p>
      <ul className="space-y-1.5">
        {rows.map(([label, count]) => (
          <li key={label} className="grid grid-cols-[minmax(0,10rem)_1fr_auto] items-center gap-2 text-xs">
            <span className="truncate text-ink" title={label}>
              {label}
            </span>
            <span className="h-2 rounded-full bg-brand/15">
              <span className="block h-2 rounded-full bg-brand" style={{ width: `${(count / max) * 100}%` }} />
            </span>
            <span className="text-muted">{count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value)) return formatDate(value);
  return Array.isArray(value) ? value.join(" · ") : String(value);
}

/** Changes detected at the source for already-published records (deadline moved, listing removed or
 * closed). Detected, never silently applied: an editor applies or dismisses each one. */
function PendingChanges({ onChanged, onError }: { onChanged: () => void; onError: (message: string) => void }) {
  const [changes, setChanges] = useState<ContentChange[]>([]);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      setChanges(await api.get<ContentChange[]>("/admin/discovery/changes?status=PENDING&limit=100"));
    } catch {
      setChanges([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function decide(change: ContentChange, apply: boolean) {
    try {
      if (change.field === "source_state") {
        await api.post(`/admin/discovery/records/${change.entity_type}/${change.entity_id}/source-state`, { confirm: apply });
      } else {
        await api.post(`/admin/discovery/changes/${change.id}/${apply ? "apply" : "dismiss"}`);
      }
      await load();
      onChanged();
    } catch (err) {
      onError(err instanceof ApiError ? err.message : "Failed to resolve the change.");
    }
  }

  if (changes.length === 0) return null;
  return (
    <section className="mb-6 rounded-2xl bg-card shadow-sm">
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="flex w-full items-center justify-between px-5 py-4 text-left">
        <span>
          <span className="font-semibold text-navy">Changes detected on published records</span>
          <span className="ml-2 badge bg-warning/15 text-[#b9770e]">{changes.length}</span>
        </span>
        <span className="text-sm text-brand">{open ? "Hide" : "Review"}</span>
      </button>
      {open && (
        <ul className="divide-y divide-line border-t border-line">
          {changes.map((change) => (
            <li key={change.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
              <div>
                <p className="font-semibold text-ink">
                  {humanize(change.entity_type)} · {humanize(change.field)}{" "}
                  <Link href={`/${RECORD_ROUTES[change.entity_type] ?? "jobs"}/${change.entity_id}`} className="text-xs font-normal text-brand">
                    Open record
                  </Link>
                </p>
                <p className="text-muted">
                  <span className="line-through">{valueText(change.old_value)}</span> → <span className="font-semibold text-ink">{valueText(change.new_value)}</span>
                  <span className="ml-2 text-xs">detected {formatDate(change.detected_at, true)}</span>
                </p>
              </div>
              <div className="flex gap-2">
                <button className="btn-primary px-3 py-1 text-xs" onClick={() => decide(change, true)}>
                  {change.field === "source_state" ? "Confirm & expire" : "Apply"}
                </button>
                <button className="btn-secondary px-3 py-1 text-xs" onClick={() => decide(change, false)}>
                  {change.field === "source_state" ? "Still active" : "Dismiss"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
