"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { OverviewCard } from "@/components/OverviewCard";
import { PageHeader, StatusBadge } from "@/components/ui";
import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { useAdminRole } from "@/lib/useAdminRole";
import {
  CONTENT_TYPES,
  CONTENT_TYPE_LABELS,
  ContentType,
  DiscoveryMetrics,
  DiscoveryRun,
  READINESS,
  READINESS_LABELS,
  Readiness,
  SOURCE_TYPES,
  SeedImport,
  SourceHealth,
  SourceTest,
  SourceType,
  formatDate,
  humanize,
} from "@/types/discovery";
import { Company, PaginatedResponse } from "@/types/models";

// Which public identifier each structured adapter needs (never a credential).
const ADAPTER_FIELD: Partial<Record<SourceType, { key: string; label: string; hint: string }>> = {
  LEVER: { key: "company", label: "Lever site name", hint: "jobs.lever.co/<site>" },
  GREENHOUSE: { key: "board_token", label: "Greenhouse board token", hint: "boards.greenhouse.io/<token>" },
  ASHBY: { key: "board_name", label: "Ashby job board name", hint: "jobs.ashbyhq.com/<name>" },
  SMARTRECRUITERS: { key: "company_identifier", label: "SmartRecruiters company id", hint: "jobs.smartrecruiters.com/<id>" },
  ORACLE: { key: "site_number", label: "Oracle Recruiting site number", hint: "…/CandidateExperience/en/sites/<site>" },
  RSS: { key: "feed_url", label: "Feed URL", hint: "RSS or Atom feed" },
};

const URL_HINT: Partial<Record<SourceType, string>> = {
  WORKDAY: "https://{tenant}.wdN.myworkdayjobs.com/{site}",
  ORACLE: "https://{pod}.fa.{dc}.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{site}",
  GREENHOUSE: "https://boards.greenhouse.io/{token}",
  LEVER: "https://jobs.lever.co/{site}",
  ASHBY: "https://jobs.ashbyhq.com/{board}",
};

const JOB_TYPES: ContentType[] = ["JOB", "INTERNSHIP", "GRADUATE_PROGRAM", "APPRENTICESHIP", "TRAINEE_PROGRAM"];
const DEFAULT_TYPES: Partial<Record<SourceType, ContentType[]>> = {
  OFFICIAL_NEWSROOM: ["INTELLIGENCE"],
  INVESTOR_RELATIONS: ["INTELLIGENCE"],
  INDUSTRY_PUBLICATION: ["INTELLIGENCE"],
  NEWS_MEDIA: ["INTELLIGENCE"],
  SCHOLARSHIP_PROVIDER: ["SCHOLARSHIP", "FELLOWSHIP"],
  UNIVERSITY: ["SCHOLARSHIP", "FELLOWSHIP"],
};
const PAGE_TYPES: SourceType[] = ["OFFICIAL_CAREER_PAGE", "UNIVERSITY", "SCHOLARSHIP_PROVIDER", "GOVERNMENT", "SUCCESSFACTORS"];

function trustLabel(level: number) {
  return ["", "Discovery only", "Reputable media", "Institutional", "Official ATS", "Official source"][level] ?? String(level);
}

function listOf(value: string): string[] {
  return value.split(/[\n,]+/).map((v) => v.trim()).filter(Boolean);
}

export default function SourcesPage() {
  const { checked } = useAdminGuard();
  const { role } = useAdminRole();
  const canManageTrust = role === "SUPER_ADMIN" || role === "ADMIN";
  const [sources, setSources] = useState<SourceHealth[]>([]);
  const [metrics, setMetrics] = useState<DiscoveryMetrics | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [runsFor, setRunsFor] = useState<SourceHealth | null>(null);
  const [editing, setEditing] = useState<SourceHealth | null>(null);
  const [runs, setRuns] = useState<DiscoveryRun[]>([]);
  const [tests, setTests] = useState<Record<string, SourceTest>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [readinessFilter, setReadinessFilter] = useState<Readiness | "">("");
  const [healthFilter, setHealthFilter] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    try {
      const [sourceList, metricData] = await Promise.all([
        api.get<SourceHealth[]>("/admin/sources"),
        api.get<DiscoveryMetrics>("/admin/discovery/metrics"),
      ]);
      setSources(sourceList);
      setMetrics(metricData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load sources.");
    }
  }, []);

  useEffect(() => {
    if (!checked) return;
    load();
    api.get<PaginatedResponse<Company>>("/admin/companies?page=1&page_size=100").then((res) => setCompanies(res.items)).catch(() => undefined);
  }, [checked, load]);

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return sources.filter(
      (s) =>
        (!readinessFilter || s.readiness === readinessFilter) &&
        (!healthFilter || s.health === healthFilter) &&
        (!term || `${s.name} ${s.organization ?? ""} ${s.company_name ?? ""} ${s.ats_provider ?? ""}`.toLowerCase().includes(term)),
    );
  }, [sources, readinessFilter, healthFilter, search]);

  async function act(source: SourceHealth, action: "run" | "pause" | "resume" | "test") {
    setBusy(`${source.id}:${action}`);
    setError(null);
    try {
      if (action === "run") {
        const run = await api.post<DiscoveryRun>(`/admin/sources/${source.id}/run`);
        setNotice(`Sync queued for ${source.name} (${humanize(run.status)}). New and changed vacancies appear in the Discovery queue when it finishes.`);
      } else if (action === "test") {
        const result = await api.post<SourceTest>(`/admin/sources/${source.id}/test`);
        setTests((current) => ({ ...current, [source.id]: result }));
        return;
      } else {
        await api.post(`/admin/sources/${source.id}/${action}`);
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed.");
    } finally {
      setBusy(null);
    }
  }

  async function importStarterPack() {
    setBusy("import");
    setError(null);
    try {
      const preview = await api.post<SeedImport>("/admin/sources/import-seed", { dry_run: true });
      const summary = `${preview.sources_created} new sources, ${preview.companies_created} new companies, ${preview.sources_updated} sources refreshed`;
      if (!window.confirm(`Import the starter company pack?\n\n${summary}.\n\nExisting sources keep their polling, trust and publishing settings.`)) return;
      const result = await api.post<SeedImport>("/admin/sources/import-seed", { dry_run: false });
      setNotice(`Starter pack imported: ${result.sources_created} sources added, ${result.sources_updated} refreshed, ${result.companies_created} companies added.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed.");
    } finally {
      setBusy(null);
    }
  }

  async function openRuns(source: SourceHealth) {
    setRunsFor(source);
    setRuns([]);
    try {
      setRuns(await api.get<DiscoveryRun[]>(`/admin/sources/${source.id}/runs?limit=20`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load runs.");
    }
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <PageHeader
        eyebrow="Research operations"
        title="Sources"
        subtitle="Official company career sites, ATS boards, feeds and institutions CareerOS syncs for current vacancies and company developments. Nothing found here is published without review unless a source is explicitly trusted."
        actions={
          <div className="flex gap-2">
            {canManageTrust && (
              <button className="btn-secondary" disabled={busy !== null} onClick={importStarterPack}>
                {busy === "import" ? "Importing…" : "Import starter pack"}
              </button>
            )}
            <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
              {showForm ? "Close" : "Add source"}
            </button>
          </div>
        }
      />

      {metrics && (
        <section className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <OverviewCard label="Active sources" value={metrics.active_sources} tone="primary" />
          <OverviewCard label="Healthy" value={metrics.healthy_sources} tone="success" />
          <OverviewCard label="Syncing automatically" value={metrics.polling_sources} tone="info" />
          <OverviewCard label="Failing" value={metrics.failing_sources} tone={metrics.failing_sources ? "danger" : "success"} />
          <OverviewCard label="Awaiting review" value={metrics.awaiting_review} tone="warning" />
        </section>
      )}
      {metrics && !metrics.flags.web_discovery && (
        <p className="mb-4 rounded-xl bg-warning/15 px-4 py-3 text-sm text-[#8a5a0a]">
          Career source sync is switched off for this deployment (CAREER_SOURCE_SYNC_ENABLED). Manual content management still works.
        </p>
      )}

      {showForm && (
        <SourceForm
          companies={companies}
          canManageTrust={canManageTrust}
          onCreated={async (name) => {
            setShowForm(false);
            setNotice(`${name} added. Use Test connection, then turn on automatic sync or Run sync now.`);
            await load();
          }}
        />
      )}

      {notice && <p className="mb-4 rounded-xl bg-brand/10 px-4 py-3 text-sm text-brand">{notice}</p>}
      {error && <p className="mb-4 rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>}

      <div className="mb-4 grid gap-3 rounded-2xl bg-card p-4 shadow-sm md:grid-cols-4">
        <input aria-label="Search sources" placeholder="Search company, source or ATS" value={search} onChange={(e) => setSearch(e.target.value)} className="md:col-span-2" />
        <select aria-label="Readiness" value={readinessFilter} onChange={(e) => setReadinessFilter(e.target.value as Readiness | "")}>
          <option value="">Any readiness</option>
          {READINESS.map((r) => (
            <option key={r} value={r}>
              {READINESS_LABELS[r]}
              {metrics?.sources_by_readiness?.[r] ? ` (${metrics.sources_by_readiness[r]})` : ""}
            </option>
          ))}
        </select>
        <select aria-label="Health" value={healthFilter} onChange={(e) => setHealthFilter(e.target.value)}>
          <option value="">Any health</option>
          {["HEALTHY", "DEGRADED", "FAILING", "PAUSED", "UNKNOWN"].map((h) => (
            <option key={h} value={h}>{humanize(h)}</option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full min-w-[1180px] text-left text-sm">
          <thead className="border-b border-line text-xs text-muted">
            <tr>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Readiness</th>
              <th className="px-4 py-3">Health</th>
              <th className="px-4 py-3">Last sync</th>
              <th className="px-4 py-3">Last failure</th>
              <th className="px-4 py-3 text-right">Items</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-muted">
                  {sources.length === 0 ? "No sources yet. Import the starter pack or add an official careers site, ATS board or newsroom feed." : "No sources match these filters."}
                </td>
              </tr>
            )}
            {visible.map((s) => (
              <SourceRow
                key={s.id}
                source={s}
                test={tests[s.id]}
                busy={busy}
                onAct={(action) => act(s, action)}
                onRuns={() => openRuns(s)}
                onEdit={() => setEditing(s)}
              />
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <EditSource
          source={editing}
          canManageTrust={canManageTrust}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setNotice(`${editing.name} updated.`);
            setEditing(null);
            await load();
          }}
        />
      )}

      {runsFor && (
        <div className="fixed inset-0 z-40 flex justify-end bg-navy/30" onClick={() => setRunsFor(null)}>
          <aside className="h-full w-full max-w-xl overflow-y-auto bg-background p-6 shadow-md" onClick={(e) => e.stopPropagation()} aria-label={`Sync runs for ${runsFor.name}`}>
            <div className="mb-4 flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-brand">Run history</p>
                <h2 className="text-lg font-bold text-navy">{runsFor.name}</h2>
              </div>
              <button className="text-sm text-muted" onClick={() => setRunsFor(null)}>Close</button>
            </div>
            {runs.length === 0 && <p className="text-sm text-muted">No runs yet.</p>}
            <ul className="space-y-3">
              {runs.map((run) => {
                const stats = run.stats_json as { possibly_removed?: number; drafts_created?: number; filtered?: number; http?: { requests?: number } };
                return (
                  <li key={run.id} className="rounded-2xl bg-card p-4 shadow-sm">
                    <div className="flex items-center justify-between">
                      <StatusBadge status={run.status} />
                      <span className="text-xs text-muted">{humanize(run.trigger)} · {formatDate(run.queued_at, true)}</span>
                    </div>
                    <p className="mt-2 text-sm text-ink">
                      {run.items_found} found · {run.items_new} new · {run.items_updated} updated · {run.items_duplicate} duplicates · {run.items_invalid} invalid ·{" "}
                      {run.items_removed} removed{stats.possibly_removed ? ` · ${stats.possibly_removed} possibly removed` : ""}
                      {stats.drafts_created ? ` · ${stats.drafts_created} drafts` : ""}
                    </p>
                    <p className="text-xs text-muted">
                      {run.duration_ms !== null ? `${(run.duration_ms / 1000).toFixed(1)}s` : ""}
                      {stats.http?.requests ? ` · ${stats.http.requests} requests` : ""}
                      {stats.filtered ? ` · ${stats.filtered} outside country scope` : ""}
                    </p>
                    {run.error_code && (
                      <p className="mt-1 text-xs text-danger">
                        {humanize(run.error_code)}
                        {run.error_message ? ` — ${run.error_message}` : ""}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          </aside>
        </div>
      )}
    </main>
  );
}

function SourceRow({
  source: s,
  test,
  busy,
  onAct,
  onRuns,
  onEdit,
}: {
  source: SourceHealth;
  test?: SourceTest;
  busy: string | null;
  onAct: (action: "run" | "pause" | "resume" | "test") => void;
  onRuns: () => void;
  onEdit: () => void;
}) {
  const scope = (s.adapter_config_json.country_filter as string[] | undefined) ?? [];
  const fetchable = s.discovery_method !== "MANUAL";
  return (
    <>
      <tr className="border-b border-line align-top last:border-0">
        <td className="px-4 py-3">
          <p className="font-semibold text-ink">{s.name}</p>
          <p className="text-xs text-muted">
            {s.company_name ?? s.organization ?? "—"} · {humanize(s.source_type)}
            {s.ats_provider ? ` · ${humanize(s.ats_provider)}` : ""}
            {s.adapter_name ? ` · adapter: ${s.adapter_name}` : ""}
          </p>
          <p className="mt-1 text-xs text-muted">
            <a className="text-brand" href={s.job_search_url ?? s.url} target="_blank" rel="noopener noreferrer">
              {s.domain ?? s.url}
            </a>
            {" · "}
            {fetchable ? `every ${Math.round(s.crawl_interval_minutes / 60)}h` : "not fetched"}
            {scope.length ? ` · scope: ${scope.join(", ")}` : ""}
          </p>
        </td>
        <td className="max-w-[260px] px-4 py-3">
          <StatusBadge status={s.readiness} label={READINESS_LABELS[s.readiness]} />
          {s.readiness_note && (
            <p className="mt-1 line-clamp-3 text-xs text-muted" title={s.readiness_note}>
              {s.readiness_note}
            </p>
          )}
        </td>
        <td className="space-y-1 px-4 py-3">
          <StatusBadge status={s.health ?? "UNKNOWN"} />
          <p className="text-xs text-muted">
            {s.polling_enabled ? "Auto sync on" : "Auto sync off"}
            {s.auto_create_draft ? " · auto drafts" : ""}
            {s.auto_publish_allowed ? " · auto-publish allowed" : ""}
          </p>
          <p className="text-xs text-muted">
            Trust {s.trust_level}/5 · {trustLabel(s.trust_level)}
          </p>
        </td>
        <td className="px-4 py-3 text-xs text-muted">
          <p className="text-ink">{formatDate(s.last_checked_at, true)}</p>
          {s.last_http_status !== null && <p>HTTP {s.last_http_status}</p>}
          {s.items_last_found !== null && <p>{s.items_last_found} listings in scope</p>}
          {s.last_run_status && (
            <p>
              {humanize(s.last_run_status)}
              {s.last_run_new ? ` · ${s.last_run_new} new` : ""}
              {s.last_run_updated ? ` · ${s.last_run_updated} updated` : ""}
              {s.last_run_removed ? ` · ${s.last_run_removed} removed` : ""}
            </p>
          )}
        </td>
        <td className="px-4 py-3">
          {s.last_error_at ? (
            <>
              <p className="text-xs font-semibold text-danger">{humanize(s.last_error_code)}</p>
              <p className="text-xs text-muted">{formatDate(s.last_error_at, true)}</p>
              {s.next_poll_after && <p className="text-xs text-muted">Backing off until {formatDate(s.next_poll_after, true)}</p>}
            </>
          ) : (
            <span className="text-muted">—</span>
          )}
        </td>
        <td className="px-4 py-3 text-right">
          <p className="font-semibold text-navy">{s.items_discovered ?? 0}</p>
          <p className="text-xs text-muted">
            {s.items_awaiting_review ?? 0} to review · {s.items_published ?? 0} published
          </p>
        </td>
        <td className="px-4 py-3">
          <div className="flex flex-col items-end gap-2">
            <button className="btn-primary px-3 py-1.5 text-xs" disabled={!s.is_active || !fetchable || busy !== null} onClick={() => onAct("run")}>
              {busy === `${s.id}:run` ? "Queuing…" : "Run sync now"}
            </button>
            <div className="flex flex-wrap justify-end gap-3 text-xs">
              <button className="text-brand disabled:text-muted" disabled={!fetchable || busy !== null} onClick={() => onAct("test")}>
                {busy === `${s.id}:test` ? "Testing…" : "Test connection"}
              </button>
              <button className="text-brand" onClick={onEdit}>Edit</button>
              <button className="text-muted hover:text-ink" disabled={busy !== null} onClick={() => onAct(s.is_active ? "pause" : "resume")}>
                {s.is_active ? "Disable" : "Enable"}
              </button>
              <button className="text-brand" onClick={onRuns}>Runs</button>
              <Link className="text-brand" href={`/discovery?source_id=${s.id}`}>Items</Link>
            </div>
          </div>
        </td>
      </tr>
      {test && (
        <tr className="border-b border-line bg-background/60">
          <td colSpan={7} className="px-4 py-3 text-xs">
            {test.ok ? (
              <p className="text-ink">
                <span className="font-semibold text-success">Connection OK</span> via {test.adapter} · HTTP {test.http_status ?? "—"} · {test.requests} requests ·{" "}
                {test.found} sample listing{test.found === 1 ? "" : "s"}
                {test.sample_titles.length ? `: ${test.sample_titles.join(" · ")}` : ""}
                {test.warnings.length ? ` · ${test.warnings.join("; ")}` : ""}
              </p>
            ) : (
              <p className="text-danger">
                <span className="font-semibold">Connection failed</span> · {humanize(test.error_code)}
                {test.error ? ` — ${test.error}` : ""}
                {test.http_status ? ` (HTTP ${test.http_status})` : ""}
              </p>
            )}
            <p className="mt-1 text-muted">Test connection reads at most five listings and stores nothing.</p>
          </td>
        </tr>
      )}
    </>
  );
}

function EditSource({
  source,
  canManageTrust,
  onClose,
  onSaved,
}: {
  source: SourceHealth;
  canManageTrust: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const config = source.adapter_config_json;
  const [polling, setPolling] = useState(source.polling_enabled);
  const [autoDraft, setAutoDraft] = useState(source.auto_create_draft);
  const [intervalHours, setIntervalHours] = useState(String(Math.round(source.crawl_interval_minutes / 60)));
  const [readiness, setReadiness] = useState<Readiness>(source.readiness);
  const [note, setNote] = useState(source.readiness_note ?? "");
  const [jobSearchUrl, setJobSearchUrl] = useState(source.job_search_url ?? "");
  const [atsProvider, setAtsProvider] = useState(source.ats_provider ?? "");
  const [scope, setScope] = useState(((config.country_filter as string[] | undefined) ?? []).join(", "));
  const [listingPages, setListingPages] = useState(((config.listing_pages as string[] | undefined) ?? []).join("\n"));
  const [linkMarker, setLinkMarker] = useState((config.job_link_contains as string | undefined) ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const nextConfig: Record<string, unknown> = { ...config, country_filter: listOf(scope) };
    const pages = listOf(listingPages);
    if (pages.length) {
      nextConfig.listing_pages = pages;
      nextConfig.job_link_contains = linkMarker.trim();
    } else {
      delete nextConfig.listing_pages;
      delete nextConfig.job_link_contains;
    }
    if (!listOf(scope).length) delete nextConfig.country_filter;
    try {
      await api.put(`/admin/sources/${source.id}`, {
        polling_enabled: polling,
        auto_create_draft: autoDraft,
        crawl_interval_minutes: Math.round(Number(intervalHours) * 60),
        readiness,
        readiness_note: note || null,
        job_search_url: jobSearchUrl || null,
        ats_provider: atsProvider ? atsProvider.toUpperCase().replace(/[^A-Z0-9_]/g, "_") : null,
        adapter_config_json: nextConfig,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-navy/30" onClick={onClose}>
      <aside className="h-full w-full max-w-xl overflow-y-auto bg-background p-6 shadow-md" onClick={(e) => e.stopPropagation()} aria-label={`Edit ${source.name}`}>
        <div className="mb-4 flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-brand">Edit source</p>
            <h2 className="text-lg font-bold text-navy">{source.name}</h2>
          </div>
          <button className="text-sm text-muted" onClick={onClose}>Close</button>
        </div>
        <form onSubmit={save} className="space-y-4 rounded-2xl bg-card p-5 shadow-sm">
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={polling} onChange={(e) => setPolling(e.target.checked)} />
            Sync automatically on its schedule
          </label>
          <Field label="Sync every (hours)" hint="Official career sources: 6h; very large boards 12h; slow sources 24h. Never less than 1h.">
            <input type="number" min={1} max={168} value={intervalHours} onChange={(e) => setIntervalHours(e.target.value)} />
          </Field>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={autoDraft} onChange={(e) => setAutoDraft(e.target.checked)} />
            Create drafts automatically for new verified vacancies (an editor still publishes)
          </label>
          <Field label="Country scope" hint="Countries or regions (e.g. AFRICA, Nigeria, United Kingdom), comma separated. Empty keeps every listing.">
            <input value={scope} onChange={(e) => setScope(e.target.value)} />
          </Field>
          <Field label="Listing pages" hint="Official pages linking to individual openings, one per line (structured-page sources).">
            <textarea rows={2} value={listingPages} onChange={(e) => setListingPages(e.target.value)} />
          </Field>
          <Field label="Opening link contains" hint="Path fragment identifying opening links, e.g. /job/">
            <input value={linkMarker} onChange={(e) => setLinkMarker(e.target.value)} />
          </Field>
          <Field label="Job search URL">
            <input type="url" value={jobSearchUrl} onChange={(e) => setJobSearchUrl(e.target.value)} />
          </Field>
          <Field label="ATS provider">
            <input value={atsProvider} onChange={(e) => setAtsProvider(e.target.value)} placeholder="WORKDAY, ORACLE_RECRUITING, SUCCESSFACTORS…" />
          </Field>
          <Field label="Readiness">
            <select value={readiness} onChange={(e) => setReadiness(e.target.value as Readiness)}>
              {READINESS.map((r) => (
                <option key={r} value={r}>{READINESS_LABELS[r]}</option>
              ))}
            </select>
          </Field>
          <Field label="Readiness note">
            <textarea rows={3} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
          {!canManageTrust && <p className="text-xs text-muted">Trust level, ownership verification and auto-publishing are changed by admins.</p>}
          {error && <p className="text-sm text-danger">{error}</p>}
          <button type="submit" className="btn-primary" disabled={saving}>{saving ? "Saving…" : "Save"}</button>
        </form>
      </aside>
    </div>
  );
}

function SourceForm({
  companies,
  canManageTrust,
  onCreated,
}: {
  companies: Company[];
  canManageTrust: boolean;
  onCreated: (name: string) => void;
}) {
  const [name, setName] = useState("");
  const [organization, setOrganization] = useState("");
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("GREENHOUSE");
  const [companyId, setCompanyId] = useState("");
  const [country, setCountry] = useState("");
  const [industry, setIndustry] = useState("");
  const [contentTypes, setContentTypes] = useState<ContentType[]>(JOB_TYPES);
  const [adapterValue, setAdapterValue] = useState("");
  const [pages, setPages] = useState("");
  const [listingPages, setListingPages] = useState("");
  const [linkMarker, setLinkMarker] = useState("/job");
  const [scope, setScope] = useState("");
  const [jobSearchUrl, setJobSearchUrl] = useState("");
  const [atsProvider, setAtsProvider] = useState("");
  const [readiness, setReadiness] = useState<Readiness>("UNVERIFIED");
  const [method, setMethod] = useState("");
  const [polling, setPolling] = useState(false);
  const [autoDraft, setAutoDraft] = useState(false);
  const [intervalHours, setIntervalHours] = useState("");
  const [trust, setTrust] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const adapterField = ADAPTER_FIELD[sourceType];
  const needsPages = PAGE_TYPES.includes(sourceType);

  function changeType(next: SourceType) {
    setSourceType(next);
    setContentTypes(DEFAULT_TYPES[next] ?? JOB_TYPES);
    setAdapterValue("");
  }

  function toggleType(type: ContentType) {
    setContentTypes((current) => (current.includes(type) ? current.filter((t) => t !== type) : [...current, type]));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const adapterConfig: Record<string, unknown> = {};
    if (adapterField && adapterValue.trim()) adapterConfig[adapterField.key] = adapterValue.trim();
    const pageList = listOf(pages);
    if (pageList.length) adapterConfig.pages = pageList;
    const listingList = listOf(listingPages);
    if (listingList.length) {
      adapterConfig.listing_pages = listingList;
      adapterConfig.job_link_contains = linkMarker.trim();
    }
    if (listOf(scope).length) adapterConfig.country_filter = listOf(scope);
    try {
      await api.post("/admin/sources", {
        name,
        organization: organization || null,
        url,
        source_type: sourceType,
        company_id: companyId || null,
        country: country || null,
        industry: industry || null,
        content_types: contentTypes,
        adapter_config_json: adapterConfig,
        discovery_method: method || null,
        polling_enabled: polling,
        auto_create_draft: autoDraft,
        crawl_interval_minutes: intervalHours ? Math.round(Number(intervalHours) * 60) : null,
        trust_level: canManageTrust && trust ? Number(trust) : null,
        job_search_url: jobSearchUrl || null,
        ats_provider: atsProvider ? atsProvider.toUpperCase().replace(/[^A-Z0-9_]/g, "_") : null,
        readiness,
      });
      onCreated(name);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add source.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="mb-6 grid gap-4 rounded-2xl bg-card p-6 shadow-sm md:grid-cols-3">
      <Field label="Name">
        <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Energy careers (Workday)" />
      </Field>
      <Field label="Organization">
        <input value={organization} onChange={(e) => setOrganization(e.target.value)} placeholder="As named by the source" />
      </Field>
      <Field label="Source type">
        <select value={sourceType} onChange={(e) => changeType(e.target.value as SourceType)}>
          {SOURCE_TYPES.map((t) => (
            <option key={t} value={t}>{humanize(t)}</option>
          ))}
        </select>
      </Field>
      <Field label="Base URL" hint={URL_HINT[sourceType]} className="md:col-span-2">
        <input required type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://boards.greenhouse.io/acme" />
      </Field>
      <Field label="Linked company">
        <select value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
          <option value="">— none —</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </Field>
      {adapterField && (
        <Field label={adapterField.label} hint={`Optional if the URL is ${adapterField.hint}`}>
          <input value={adapterValue} onChange={(e) => setAdapterValue(e.target.value)} />
        </Field>
      )}
      {needsPages && (
        <>
          <Field label="Listing pages" hint="Official pages that link to individual openings (one per line)" className="md:col-span-2">
            <textarea rows={2} value={listingPages} onChange={(e) => setListingPages(e.target.value)} />
          </Field>
          <Field label="Opening link contains" hint="e.g. /job/">
            <input value={linkMarker} onChange={(e) => setLinkMarker(e.target.value)} />
          </Field>
          <Field label="Or specific page URLs" hint="One per line; pages with schema.org data are read without AI" className="md:col-span-2">
            <textarea rows={2} value={pages} onChange={(e) => setPages(e.target.value)} />
          </Field>
          <Field label="Discovery method">
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="">Default</option>
              <option value="STRUCTURED_DATA">Structured data (no AI)</option>
              <option value="AI_RESEARCH">AI research when no structured data</option>
              <option value="RSS">RSS feed</option>
              <option value="MANUAL">Manual only</option>
            </select>
          </Field>
        </>
      )}
      <Field label="Country scope" hint="e.g. AFRICA, Nigeria — empty keeps every listing">
        <input value={scope} onChange={(e) => setScope(e.target.value)} />
      </Field>
      <Field label="Job search URL">
        <input type="url" value={jobSearchUrl} onChange={(e) => setJobSearchUrl(e.target.value)} />
      </Field>
      <Field label="ATS provider">
        <input value={atsProvider} onChange={(e) => setAtsProvider(e.target.value)} placeholder="WORKDAY" />
      </Field>
      <Field label="Readiness">
        <select value={readiness} onChange={(e) => setReadiness(e.target.value as Readiness)}>
          {READINESS.map((r) => (
            <option key={r} value={r}>{READINESS_LABELS[r]}</option>
          ))}
        </select>
      </Field>
      <Field label="Country">
        <input value={country} onChange={(e) => setCountry(e.target.value)} />
      </Field>
      <Field label="Industry">
        <input value={industry} onChange={(e) => setIndustry(e.target.value)} />
      </Field>
      <Field label="Sync every (hours)" hint="Default depends on the source type (official career sources: 6h)">
        <input type="number" min={1} max={168} value={intervalHours} onChange={(e) => setIntervalHours(e.target.value)} />
      </Field>
      <fieldset className="md:col-span-2">
        <legend className="mb-2 text-xs font-medium text-muted">Content this source publishes</legend>
        <div className="flex flex-wrap gap-2">
          {CONTENT_TYPES.map((type) => (
            <label key={type} className={`cursor-pointer rounded-full px-3 py-1.5 text-xs font-semibold shadow-sm ${contentTypes.includes(type) ? "bg-brand text-white" : "bg-white text-muted"}`}>
              <input type="checkbox" className="sr-only" checked={contentTypes.includes(type)} onChange={() => toggleType(type)} />
              {CONTENT_TYPE_LABELS[type]}
            </label>
          ))}
        </div>
      </fieldset>
      {canManageTrust && (
        <Field label="Trust level" hint="Trust never grants publish permission">
          <select value={trust} onChange={(e) => setTrust(e.target.value)}>
            <option value="">Default for type</option>
            {[5, 4, 3, 2, 1].map((level) => (
              <option key={level} value={level}>{level} — {trustLabel(level)}</option>
            ))}
          </select>
        </Field>
      )}
      <label className="flex items-center gap-2 text-sm text-ink md:col-span-3">
        <input type="checkbox" checked={polling} onChange={(e) => setPolling(e.target.checked)} />
        Sync this source automatically on its schedule
      </label>
      <label className="flex items-center gap-2 text-sm text-ink md:col-span-3">
        <input type="checkbox" checked={autoDraft} onChange={(e) => setAutoDraft(e.target.checked)} />
        Create drafts automatically for new verified vacancies (an editor still publishes)
      </label>
      {error && <p className="text-sm text-danger md:col-span-3">{error}</p>}
      <div className="md:col-span-3">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Adding…" : "Add source"}
        </button>
      </div>
    </form>
  );
}

function Field({ label, hint, className, children }: { label: string; hint?: string; className?: string; children: React.ReactNode }) {
  return (
    <label className={`block text-sm ${className ?? ""}`}>
      <span className="mb-1 block text-xs font-medium text-muted">{label}</span>
      <span className="block [&>input]:w-full [&>select]:w-full [&>textarea]:w-full">{children}</span>
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}
