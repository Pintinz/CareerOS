"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { StatusBadge } from "@/components/ui";
import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { CONTENT_TYPE_LABELS, ContentChange, DiscoveryReview, formatDate, humanize } from "@/types/discovery";
import { Company, PaginatedResponse } from "@/types/models";

const INTELLIGENCE_CATEGORIES = [
  "LEADERSHIP", "TECHNOLOGY", "AUTOMATION", "INVESTMENTS", "HIRING", "PROJECTS", "ACQUISITION", "PLANT_EXPANSION",
  "MANUFACTURING", "ENERGY", "FINANCE", "AI", "GRADUATE_RECRUITMENT", "OPERATIONS", "OTHER",
];

function text(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(" · ") : "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function toDateInput(value: unknown): string {
  return typeof value === "string" && value ? value.slice(0, 10) : "";
}

export default function DiscoveryReviewPage() {
  const { checked } = useAdminGuard();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [review, setReview] = useState<DiscoveryReview | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [form, setForm] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.get<DiscoveryReview>(`/admin/discovery/${params.id}/review`);
      setReview(data);
      const e = data.extracted;
      const kind = data.item.item_type;
      setForm({
        title: String(e.title ?? e.name ?? e.headline ?? data.item.detected_title ?? ""),
        company_id: data.item.company_id ?? "",
        location: String(e.location ?? ""),
        country: String(e.country ?? ""),
        summary: String(e.summary ?? ""),
        description: String(e.description ?? ""),
        application_url: String(e.application_url ?? e.official_application_url ?? ""),
        deadline: toDateInput(e.application_deadline ?? e.deadline),
        category: String(e.category ?? (kind === "INTELLIGENCE" ? "OTHER" : "")),
        career_relevance: String(e.career_relevance ?? ""),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load this item.");
    }
  }, [params.id]);

  useEffect(() => {
    if (!checked) return;
    load();
    api.get<PaginatedResponse<Company>>("/admin/companies?page=1&page_size=100").then((res) => setCompanies(res.items)).catch(() => undefined);
  }, [checked, load]);

  const edits = useMemo(() => {
    if (!review) return {};
    const payload: Record<string, unknown> = {};
    const original = review.extracted;
    const originalTitle = String(original.title ?? original.name ?? original.headline ?? "");
    if (form.title && form.title !== originalTitle) payload.title = form.title;
    for (const key of ["location", "country", "summary", "description", "application_url", "career_relevance", "category"]) {
      const before = String(original[key] ?? (key === "application_url" ? original.official_application_url ?? "" : ""));
      if (form[key] !== undefined && form[key] !== before && form[key] !== "") payload[key] = form[key];
    }
    const originalDeadline = toDateInput(original.application_deadline ?? original.deadline);
    if (form.deadline && form.deadline !== originalDeadline) payload.deadline = new Date(`${form.deadline}T23:59:00Z`).toISOString();
    if (form.company_id) payload.company_id = form.company_id;
    return payload;
  }, [form, review]);

  async function run(action: () => Promise<void>) {
    setWorking(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed.");
    } finally {
      setWorking(false);
    }
  }

  const createDraft = () =>
    run(async () => {
      const result = await api.post<{ entity_type: string; draft_id: string }>(`/admin/discovery/${params.id}/create-draft`, edits);
      const dest = result.entity_type === "JOB" ? "jobs" : result.entity_type === "SCHOLARSHIP" ? "scholarships" : "intelligence";
      router.push(`/${dest}/${result.draft_id}`);
    });

  const publish = () =>
    run(async () => {
      const result = await api.post<{ entity_type: string; entity_id: string; notified_devices: number }>(`/admin/discovery/${params.id}/publish`, edits);
      setNotice(`Published. It is now live in the app${result.notified_devices ? ` and ${result.notified_devices} follower device(s) were notified` : ""}.`);
      await load();
    });

  const decide = (action: "ignore" | "reject") =>
    run(async () => {
      await api.post(`/admin/discovery/${params.id}/${action}`);
      router.push("/discovery");
    });

  const createCompany = () =>
    run(async () => {
      const proposal = review?.evidence.proposed_company;
      if (!proposal) return;
      const company = await api.post<Company>(`/admin/discovery/${params.id}/create-company`, {
        name: proposal.name,
        website_url: proposal.website_url,
        career_url: proposal.career_url,
        industry: proposal.industry,
      });
      setCompanies((list) => [company, ...list.filter((c) => c.id !== company.id)]);
      setForm((f) => ({ ...f, company_id: company.id }));
      setNotice(`Company “${company.name}” created. Add its logo and details on the Companies page.`);
    });

  const decideChange = (change: ContentChange, apply: boolean) =>
    run(async () => {
      if (change.field === "source_state") {
        await api.post(`/admin/discovery/records/${change.entity_type}/${change.entity_id}/source-state`, { confirm: apply });
      } else {
        await api.post(`/admin/discovery/changes/${change.id}/${apply ? "apply" : "dismiss"}`);
      }
      await load();
    });

  if (!checked) return null;
  if (!review) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        {error ? <p className="text-sm text-danger">{error}</p> : <p className="text-sm text-muted">Loading…</p>}
      </main>
    );
  }

  const { item, evidence, source, current_record: current } = review;
  const kind = item.item_type;
  const isJob = ["JOB", "INTERNSHIP", "GRADUATE_PROGRAM"].includes(kind);
  const isIntelligence = kind === "INTELLIGENCE";
  const decided = ["IGNORED", "REJECTED", "PUBLISHED"].includes(item.status);

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/discovery" className="text-sm text-muted hover:text-ink">← Discovery queue</Link>
          <p className="mt-2 text-xs font-semibold uppercase tracking-wider text-brand">{CONTENT_TYPE_LABELS[kind]} · review</p>
          <h1 className="text-2xl font-bold text-navy">{item.detected_title}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <StatusBadge status={item.status} />
            <StatusBadge status={item.verification_status} />
            {evidence.injection_suspected && <StatusBadge status="FAILED" label="Instruction-like page text detected" />}
          </div>
        </div>
        {!decided && (
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary" disabled={working} onClick={() => decide("ignore")}>Ignore</button>
            <button className="btn-secondary text-danger" disabled={working} onClick={() => decide("reject")}>Reject</button>
            {!item.created_draft_id && !item.matched_entity_id && (
              <button className="btn-secondary" disabled={working} onClick={createDraft}>Create draft</button>
            )}
            <button className="btn-primary" disabled={working || !review.can_publish} onClick={publish} title={review.publish_blockers[0]}>
              Publish
            </button>
          </div>
        )}
      </div>

      {review.publish_blockers.length > 0 && (
        <ul className="mb-4 space-y-1 rounded-xl bg-warning/15 px-4 py-3 text-sm text-[#8a5a0a]">
          {review.publish_blockers.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      )}
      {notice && <p className="mb-4 rounded-xl bg-brand/10 px-4 py-3 text-sm text-brand">{notice}</p>}
      {error && <p className="mb-4 rounded-xl bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ------------------------------------------------------------------ SOURCE EVIDENCE */}
        <section aria-labelledby="evidence-title" className="space-y-4">
          <div className="rounded-2xl bg-card p-6 shadow-sm">
            <h2 id="evidence-title" className="text-sm font-semibold text-navy">Source evidence</h2>
            <dl className="mt-4 grid grid-cols-[10rem_1fr] gap-x-4 gap-y-3 text-sm">
              <dt className="text-muted">Source quality</dt>
              <dd className="font-semibold text-ink">{evidence.source_quality ?? humanize(source.source_type)}</dd>
              <dt className="text-muted">Source</dt>
              <dd>
                {source.name} · trust {source.trust_level}/5
                {evidence.source_ownership_verified ? " · ownership verified" : " · ownership not yet verified"}
              </dd>
              <dt className="text-muted">Matched organization</dt>
              <dd>
                {evidence.matched_organization ? (
                  `${evidence.matched_organization.name} (by ${humanize(evidence.matched_organization.method)})`
                ) : evidence.proposed_company ? (
                  <span>
                    Not in CareerOS — proposed: <strong>{evidence.proposed_company.name}</strong>{" "}
                    <button className="text-brand" disabled={working} onClick={createCompany}>Create company</button>
                  </span>
                ) : (
                  "—"
                )}
              </dd>
              <dt className="text-muted">Original title</dt>
              <dd>{item.detected_title}</dd>
              <dt className="text-muted">Original URL</dt>
              <dd className="break-all">
                <a href={item.original_url} target="_blank" rel="noreferrer noopener" className="text-brand">{item.original_url}</a>
              </dd>
              {item.canonical_url && item.canonical_url !== item.original_url && (
                <>
                  <dt className="text-muted">Canonical URL</dt>
                  <dd className="break-all">{item.canonical_url}</dd>
                </>
              )}
              <dt className="text-muted">External job id</dt>
              <dd>{text(evidence.external_id)}</dd>
              {evidence.requisition_id && (
                <>
                  <dt className="text-muted">Requisition</dt>
                  <dd>{evidence.requisition_id}</dd>
                </>
              )}
              <dt className="text-muted">Published</dt>
              <dd>{formatDate(item.published_at)}</dd>
              <dt className="text-muted">Deadline</dt>
              <dd>{formatDate(item.deadline)}</dd>
              <dt className="text-muted">Method</dt>
              <dd>
                {humanize(evidence.discovery_method)}
                {evidence.ai_provider ? ` · ${evidence.ai_provider}${evidence.ai_model ? ` (${evidence.ai_model})` : ""}` : ""}
                {item.confidence !== null ? ` · ${Math.round(item.confidence * 100)}% confidence` : ""}
              </dd>
              <dt className="text-muted">Source verified</dt>
              <dd>{formatDate(evidence.verified_at, true)}</dd>
            </dl>
          </div>

          <div className="rounded-2xl bg-card p-6 shadow-sm">
            <h3 className="text-sm font-semibold text-navy">Why this was accepted</h3>
            <ul className="mt-3 space-y-2 text-sm">
              {(evidence.checks ?? []).map((check) => (
                <li key={check} className="flex gap-2"><span className="text-success" aria-hidden>✓</span>{check}</li>
              ))}
              {(evidence.flags ?? []).map((flag) => (
                <li key={flag} className="flex gap-2 text-danger"><span aria-hidden>!</span>{humanize(flag)}</li>
              ))}
              {(evidence.dropped_fields ?? []).length > 0 && (
                <li className="text-[#8a5a0a]">Dropped because the page did not support them: {evidence.dropped_fields!.map(humanize).join(", ")}</li>
              )}
              {evidence.injection_markers && evidence.injection_markers.length > 0 && (
                <li className="text-danger">Page text that looked like instructions (treated as data): “{evidence.injection_markers.join("”, “")}”</li>
              )}
              {(evidence.dedup ?? []).length > 0 && <li className="text-muted">Duplicate checks: {evidence.dedup!.map(humanize).join(", ")}</li>}
              {(evidence.auto_publish_blocked_by ?? []).length > 0 && (
                <li className="text-muted">Not auto-published: {evidence.auto_publish_blocked_by!.join("; ")}</li>
              )}
            </ul>
            <button className="mt-4 text-xs text-brand" onClick={() => setShowRaw((v) => !v)}>
              {showRaw ? "Hide" : "Show"} raw source payload
            </button>
            {showRaw && (
              <pre className="mt-2 max-h-80 overflow-auto rounded-xl bg-background p-3 text-xs text-ink">
                {JSON.stringify(review.raw_payload, null, 2)}
              </pre>
            )}
          </div>

          {review.duplicate_of && (
            <div className="rounded-2xl bg-card p-6 text-sm shadow-sm">
              <h3 className="text-sm font-semibold text-navy">Duplicate of</h3>
              <Link href={`/discovery/${review.duplicate_of.id}`} className="mt-2 block font-semibold text-brand">
                {review.duplicate_of.detected_title}
              </Link>
              <p className="text-xs text-muted">{review.duplicate_of.source_name}</p>
            </div>
          )}
        </section>

        {/* ------------------------------------------------------------------ CAREEROS RECORD */}
        <section aria-labelledby="record-title" className="space-y-4">
          {current && (
            <div className="rounded-2xl bg-card p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-navy">Existing CareerOS record</h2>
                <StatusBadge status={String(current.status)} />
              </div>
              <p className="mt-2 text-lg font-semibold text-navy">{text(current.title ?? current.name ?? current.headline)}</p>
              {typeof current.source_state === "string" && current.source_state !== "ACTIVE" && <StatusBadge status={current.source_state} />}
              <dl className="mt-3 grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 text-sm">
                {Object.entries(current)
                  .filter(([key]) => !["id", "entity_type", "status", "source_state", "title", "name", "headline", "company_id"].includes(key))
                  .map(([key, value]) => (
                    <div key={key} className="contents">
                      <dt className="text-muted">{humanize(key)}</dt>
                      <dd className="break-words">{text(value)}</dd>
                    </div>
                  ))}
              </dl>
              {review.pending_changes.length > 0 && (
                <div className="mt-5">
                  <h3 className="text-sm font-semibold text-[#b9770e]">Changes detected at the source</h3>
                  <ul className="mt-2 space-y-3">
                    {review.pending_changes.map((change) => (
                      <li key={change.id} className="rounded-xl border border-warning/40 bg-warning/5 p-3 text-sm">
                        <p className="font-semibold text-ink">{humanize(change.field)}</p>
                        <p className="mt-1 text-muted">
                          <span className="line-through">{text(change.old_value)}</span> → <span className="font-semibold text-ink">{text(change.new_value)}</span>
                        </p>
                        <p className="text-xs text-muted">Detected {formatDate(change.detected_at, true)}</p>
                        <div className="mt-2 flex gap-2">
                          <button className="btn-primary px-3 py-1 text-xs" disabled={working} onClick={() => decideChange(change, true)}>
                            {change.field === "source_state" ? "Confirm & expire" : "Apply change"}
                          </button>
                          <button className="btn-secondary px-3 py-1 text-xs" disabled={working} onClick={() => decideChange(change, false)}>
                            {change.field === "source_state" ? "Still active" : "Dismiss"}
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {!current && (
            <div className="rounded-2xl bg-card p-6 shadow-sm">
              <h2 id="record-title" className="text-sm font-semibold text-navy">CareerOS record</h2>
              <p className="mt-1 text-xs text-muted">Prefilled from the validated source facts. Only fields you change override them; empty facts stay empty.</p>
              <div className="mt-4 grid gap-4">
                <EditField label={isIntelligence ? "Headline" : kind === "SCHOLARSHIP" || kind === "FELLOWSHIP" ? "Name" : "Title"} changed={"title" in edits}>
                  <input value={form.title ?? ""} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                </EditField>
                {(isJob || isIntelligence) && (
                  <EditField label={isJob ? "Company (required)" : "Company"} changed={Boolean(form.company_id && form.company_id !== item.company_id)}>
                    <select value={form.company_id ?? ""} onChange={(e) => setForm({ ...form, company_id: e.target.value })}>
                      <option value="">— select —</option>
                      {companies.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </EditField>
                )}
                {!isIntelligence && (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {isJob && (
                      <EditField label="Location" changed={"location" in edits}>
                        <input value={form.location ?? ""} onChange={(e) => setForm({ ...form, location: e.target.value })} />
                      </EditField>
                    )}
                    <EditField label="Country" changed={"country" in edits}>
                      <input value={form.country ?? ""} onChange={(e) => setForm({ ...form, country: e.target.value })} />
                    </EditField>
                    <EditField label="Deadline" changed={"deadline" in edits}>
                      <input type="date" value={form.deadline ?? ""} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
                    </EditField>
                  </div>
                )}
                {!isIntelligence && (
                  <EditField label="Official application URL" changed={"application_url" in edits}>
                    <input type="url" value={form.application_url ?? ""} onChange={(e) => setForm({ ...form, application_url: e.target.value })} />
                  </EditField>
                )}
                {isIntelligence && (
                  <EditField label="Category" changed={"category" in edits}>
                    <select value={form.category ?? "OTHER"} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                      {INTELLIGENCE_CATEGORIES.map((c) => (
                        <option key={c} value={c}>{humanize(c)}</option>
                      ))}
                    </select>
                  </EditField>
                )}
                <EditField label={isIntelligence ? "Source fact (short summary)" : "Summary"} changed={"summary" in edits}>
                  <textarea rows={3} maxLength={500} value={form.summary ?? ""} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
                </EditField>
                {isIntelligence && (
                  <EditField label="Career relevance (hedged interpretation)" changed={"career_relevance" in edits} hint="e.g. “This may increase the relevance of controls skills.” Never claim hiring the source doesn't state.">
                    <textarea rows={3} maxLength={1000} value={form.career_relevance ?? ""} onChange={(e) => setForm({ ...form, career_relevance: e.target.value })} />
                  </EditField>
                )}
                {!isIntelligence && (
                  <EditField label="Description" changed={"description" in edits}>
                    <textarea rows={8} value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
                  </EditField>
                )}
              </div>
              <ExtractedFacts extracted={review.extracted} />
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function EditField({ label, changed, hint, children }: { label: string; changed?: boolean; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 flex items-center gap-2 text-xs font-medium text-muted">
        {label}
        {changed && <span className="badge bg-warning/15 px-2 py-0.5 text-[10px] text-[#b9770e]">Edited</span>}
      </span>
      <span className={`block rounded-lg [&>input]:w-full [&>select]:w-full [&>textarea]:w-full ${changed ? "ring-2 ring-warning/50" : ""}`}>{children}</span>
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

const HIDDEN_FACTS = new Set(["title", "name", "headline", "summary", "description", "source_url", "content_type", "confidence", "source_external_id", "career_relevance"]);

function ExtractedFacts({ extracted }: { extracted: Record<string, unknown> }) {
  const facts = Object.entries(extracted).filter(([key, value]) => !HIDDEN_FACTS.has(key) && value !== null && !(Array.isArray(value) && value.length === 0));
  if (facts.length === 0) return null;
  return (
    <div className="mt-6 border-t border-line pt-4">
      <h3 className="text-sm font-semibold text-navy">Other facts stated by the source</h3>
      <dl className="mt-3 grid grid-cols-[10rem_1fr] gap-x-4 gap-y-2 text-sm">
        {facts.map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-muted">{humanize(key)}</dt>
            <dd className="break-words">{text(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
