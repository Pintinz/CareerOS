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
  SOURCE_TYPES,
  SourceHealth,
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
  RSS: { key: "feed_url", label: "Feed URL", hint: "RSS or Atom feed" },
};

const DEFAULT_TYPES: Partial<Record<SourceType, ContentType[]>> = {
  OFFICIAL_NEWSROOM: ["INTELLIGENCE"],
  INVESTOR_RELATIONS: ["INTELLIGENCE"],
  INDUSTRY_PUBLICATION: ["INTELLIGENCE"],
  NEWS_MEDIA: ["INTELLIGENCE"],
  SCHOLARSHIP_PROVIDER: ["SCHOLARSHIP", "FELLOWSHIP"],
  UNIVERSITY: ["SCHOLARSHIP", "FELLOWSHIP"],
};

function trustLabel(level: number) {
  return ["", "Discovery only", "Reputable media", "Institutional", "Official ATS", "Official source"][level] ?? String(level);
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
  const [runs, setRuns] = useState<DiscoveryRun[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

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

  const companyName = useMemo(() => Object.fromEntries(companies.map((c) => [c.id, c.name])), [companies]);

  async function act(source: SourceHealth, action: "run" | "pause" | "resume") {
    setBusy(`${source.id}:${action}`);
    setError(null);
    try {
      if (action === "run") {
        const run = await api.post<DiscoveryRun>(`/admin/sources/${source.id}/run`);
        setNotice(`Discovery queued for ${source.name} (${humanize(run.status)}). Results appear in the Discovery queue when the run finishes.`);
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
        subtitle="Official career sites, ATS boards, feeds and institutions CareerOS checks for new opportunities and company developments. Nothing found here is published without review unless a source is explicitly trusted."
        actions={
          <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Close" : "Add source"}
          </button>
        }
      />

      {metrics && (
        <section className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <OverviewCard label="Active sources" value={metrics.active_sources} tone="primary" />
          <OverviewCard label="Polling automatically" value={metrics.polling_sources} tone="info" />
          <OverviewCard label="Failing sources" value={metrics.failing_sources} tone={metrics.failing_sources ? "danger" : "success"} />
          <OverviewCard label="Awaiting review" value={metrics.awaiting_review} tone="warning" />
        </section>
      )}
      {metrics && !metrics.flags.web_discovery && (
        <p className="mb-4 rounded-xl bg-warning/15 px-4 py-3 text-sm text-[#8a5a0a]">
          Web discovery is switched off for this deployment (WEB_DISCOVERY_ENABLED). Manual content management still works.
        </p>
      )}

      {showForm && (
        <SourceForm
          companies={companies}
          canManageTrust={canManageTrust}
          onCreated={async (name) => {
            setShowForm(false);
            setNotice(`${name} added. Turn on polling or use Run discovery to check it.`);
            await load();
          }}
        />
      )}

      {notice && <p className="mb-4 rounded-xl bg-brand/10 px-4 py-3 text-sm text-brand">{notice}</p>}
      {error && <p className="mb-4 rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>}

      <div className="overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Trust</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last checked</th>
              <th className="px-4 py-3">Last success</th>
              <th className="px-4 py-3">Last failure</th>
              <th className="px-4 py-3 text-right">Items</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sources.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-muted">
                  No sources yet. Add an official careers page, ATS board or newsroom feed to start discovering content.
                </td>
              </tr>
            )}
            {sources.map((s) => (
              <tr key={s.id} className="border-b border-line align-top last:border-0">
                <td className="px-4 py-3">
                  <p className="font-semibold text-ink">{s.name}</p>
                  <p className="text-xs text-muted">
                    {humanize(s.source_type)} · {s.domain ?? s.url}
                    {s.company_id && companyName[s.company_id] ? ` · ${companyName[s.company_id]}` : ""}
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    {s.content_types.map((t) => CONTENT_TYPE_LABELS[t]).join(", ") || "No content types"} · every{" "}
                    {Math.round(s.crawl_interval_minutes / 60)}h{s.adapter_available === false ? " · no automatic adapter" : ""}
                  </p>
                </td>
                <td className="px-4 py-3">
                  <p className="font-semibold text-navy">{s.trust_level}/5</p>
                  <p className="text-xs text-muted">{trustLabel(s.trust_level)}</p>
                </td>
                <td className="space-y-1 px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    <StatusBadge status={s.is_active ? "ACTIVE" : "INACTIVE"} label={s.is_active ? "Active" : "Paused"} />
                    <StatusBadge status={s.verification_status} label={s.verification_status === "VERIFIED" ? "Ownership verified" : humanize(s.verification_status)} />
                  </div>
                  <p className="text-xs text-muted">
                    {s.polling_enabled ? "Polling on" : "Polling off"}
                    {s.auto_publish_allowed ? " · auto-publish allowed" : ""}
                  </p>
                  {s.last_run_status && <StatusBadge status={s.last_run_status} label={`Last run: ${humanize(s.last_run_status)}`} />}
                </td>
                <td className="px-4 py-3 text-muted">{formatDate(s.last_checked_at, true)}</td>
                <td className="px-4 py-3 text-muted">{formatDate(s.last_successful_fetch_at, true)}</td>
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
                    <button
                      className="btn-primary px-3 py-1.5 text-xs"
                      disabled={!s.is_active || busy !== null}
                      onClick={() => act(s, "run")}
                    >
                      {busy === `${s.id}:run` ? "Queuing…" : "Run discovery"}
                    </button>
                    <div className="flex gap-3 text-xs">
                      <button className="text-muted hover:text-ink" disabled={busy !== null} onClick={() => act(s, s.is_active ? "pause" : "resume")}>
                        {s.is_active ? "Pause" : "Resume"}
                      </button>
                      <button className="text-brand" onClick={() => openRuns(s)}>Runs</button>
                      <Link className="text-brand" href={`/discovery?source_id=${s.id}`}>Items</Link>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {runsFor && (
        <div className="fixed inset-0 z-40 flex justify-end bg-navy/30" onClick={() => setRunsFor(null)}>
          <aside
            className="h-full w-full max-w-xl overflow-y-auto bg-background p-6 shadow-md"
            onClick={(e) => e.stopPropagation()}
            aria-label={`Discovery runs for ${runsFor.name}`}
          >
            <div className="mb-4 flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-brand">Run history</p>
                <h2 className="text-lg font-bold text-navy">{runsFor.name}</h2>
              </div>
              <button className="text-sm text-muted" onClick={() => setRunsFor(null)}>Close</button>
            </div>
            {runs.length === 0 && <p className="text-sm text-muted">No runs yet.</p>}
            <ul className="space-y-3">
              {runs.map((run) => (
                <li key={run.id} className="rounded-2xl bg-card p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <StatusBadge status={run.status} />
                    <span className="text-xs text-muted">
                      {humanize(run.trigger)} · {formatDate(run.queued_at, true)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-ink">
                    {run.items_found} found · {run.items_new} new · {run.items_updated} updated · {run.items_duplicate} duplicates ·{" "}
                    {run.items_invalid} invalid · {run.items_removed} removed
                  </p>
                  {run.duration_ms !== null && <p className="text-xs text-muted">{(run.duration_ms / 1000).toFixed(1)}s</p>}
                  {run.error_code && (
                    <p className="mt-1 text-xs text-danger">
                      {humanize(run.error_code)}
                      {run.error_message ? ` — ${run.error_message}` : ""}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </aside>
        </div>
      )}
    </main>
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
  const [sourceType, setSourceType] = useState<SourceType>("LEVER");
  const [companyId, setCompanyId] = useState("");
  const [country, setCountry] = useState("");
  const [industry, setIndustry] = useState("");
  const [contentTypes, setContentTypes] = useState<ContentType[]>(["JOB", "INTERNSHIP", "GRADUATE_PROGRAM"]);
  const [adapterValue, setAdapterValue] = useState("");
  const [pages, setPages] = useState("");
  const [method, setMethod] = useState("");
  const [polling, setPolling] = useState(false);
  const [intervalHours, setIntervalHours] = useState("");
  const [trust, setTrust] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const adapterField = ADAPTER_FIELD[sourceType];
  const needsPages = ["OFFICIAL_CAREER_PAGE", "UNIVERSITY", "SCHOLARSHIP_PROVIDER", "GOVERNMENT", "SUCCESSFACTORS", "ORACLE"].includes(sourceType);

  function changeType(next: SourceType) {
    setSourceType(next);
    setContentTypes(DEFAULT_TYPES[next] ?? ["JOB", "INTERNSHIP", "GRADUATE_PROGRAM"]);
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
    const pageList = pages.split(/\s+/).map((p) => p.trim()).filter(Boolean);
    if (pageList.length) adapterConfig.pages = pageList;
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
        crawl_interval_minutes: intervalHours ? Math.round(Number(intervalHours) * 60) : null,
        trust_level: canManageTrust && trust ? Number(trust) : null,
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
        <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Energy careers (Lever)" />
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
      <Field label="Base URL" className="md:col-span-2">
        <input required type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://jobs.lever.co/acme" />
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
        <Field label="Official page URLs" hint="One per line; pages with schema.org data are read without AI" className="md:col-span-2">
          <textarea rows={3} value={pages} onChange={(e) => setPages(e.target.value)} />
        </Field>
      )}
      {needsPages && (
        <Field label="Discovery method">
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="">Default</option>
            <option value="STRUCTURED_DATA">Structured data (no AI)</option>
            <option value="AI_RESEARCH">AI research when no structured data</option>
            <option value="RSS">RSS feed</option>
            <option value="MANUAL">Manual only</option>
          </select>
        </Field>
      )}
      <Field label="Country">
        <input value={country} onChange={(e) => setCountry(e.target.value)} />
      </Field>
      <Field label="Industry">
        <input value={industry} onChange={(e) => setIndustry(e.target.value)} />
      </Field>
      <Field label="Check every (hours)" hint="Default depends on the source type">
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
        Check this source automatically on its schedule
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
