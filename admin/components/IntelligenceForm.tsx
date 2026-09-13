"use client";

import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/apiClient";
import { Company, ContentStatus, IntelligenceCategory, IntelligencePostAdmin, PaginatedResponse, SourceType } from "@/types/models";

const CATEGORIES: IntelligenceCategory[] = [
  "LEADERSHIP", "TECHNOLOGY", "AUTOMATION", "INVESTMENTS", "HIRING", "PROJECTS", "ACQUISITION",
  "PLANT_EXPANSION", "OPERATIONS", "AI", "MANUFACTURING", "ENERGY", "FINANCE", "GRADUATE_RECRUITMENT", "OTHER",
];
const SOURCE_TYPES: SourceType[] = ["OFFICIAL_CAREER_PAGE", "OFFICIAL_NEWSROOM", "RSS", "LEVER", "ASHBY", "OTHER"];

type FormState = {
  company_id: string;
  headline: string;
  category: IntelligenceCategory;
  thumbnail_url: string;
  post_image_url: string;
  summary: string;
  full_content: string;
  why_it_matters: string;
  relevant_roles: string;
  relevant_skills: string;
  source_type: SourceType;
  source_url: string;
  is_verified: boolean;
  is_featured: boolean;
  status: ContentStatus;
};

const EMPTY_STATE: FormState = {
  company_id: "", headline: "", category: "OTHER", thumbnail_url: "", post_image_url: "", summary: "",
  full_content: "", why_it_matters: "", relevant_roles: "", relevant_skills: "", source_type: "OTHER",
  source_url: "", is_verified: false, is_featured: false, status: "DRAFT",
};

function toFormState(p: IntelligencePostAdmin): FormState {
  return {
    company_id: p.company_id ?? "", headline: p.headline, category: p.category,
    thumbnail_url: p.thumbnail_url ?? "", post_image_url: p.post_image_url ?? "", summary: p.summary ?? "",
    full_content: p.full_content ?? "", why_it_matters: p.why_it_matters ?? "",
    relevant_roles: (p.relevant_roles ?? []).join("\n"), relevant_skills: (p.relevant_skills ?? []).join("\n"),
    source_type: p.source_type, source_url: p.source_url ?? "", is_verified: p.is_verified,
    is_featured: p.is_featured, status: p.status,
  };
}

function linesToList(value: string): string[] | null {
  const lines = value.split("\n").map((l) => l.trim()).filter(Boolean);
  return lines.length > 0 ? lines : null;
}

const inputClass = "w-full rounded-xl border border-line px-3 py-2 text-sm";
const labelClass = "mb-1 block text-xs text-muted";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      {children}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-card p-6 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold text-navy">{title}</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>
    </div>
  );
}

export function IntelligenceForm({
  post, onSaved,
}: {
  post?: IntelligencePostAdmin;
  onSaved: (p: IntelligencePostAdmin) => void;
}) {
  const [state, setState] = useState<FormState>(post ? toFormState(post) : EMPTY_STATE);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<PaginatedResponse<Company>>("/admin/companies?page=1&page_size=100").then((res) => setCompanies(res.items));
  }, []);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        company_id: state.company_id || null,
        headline: state.headline,
        category: state.category,
        thumbnail_url: state.thumbnail_url || null,
        post_image_url: state.post_image_url || null,
        summary: state.summary || null,
        full_content: state.full_content || null,
        why_it_matters: state.why_it_matters || null,
        relevant_roles: linesToList(state.relevant_roles),
        relevant_skills: linesToList(state.relevant_skills),
        source_type: state.source_type,
        source_url: state.source_url || null,
        is_verified: state.is_verified,
        is_featured: state.is_featured,
        status: state.status,
      };
      const saved = post
        ? await api.put<IntelligencePostAdmin>(`/admin/intelligence/${post.id}`, payload)
        : await api.post<IntelligencePostAdmin>("/admin/intelligence", payload);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save intelligence post.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Section title="Basic Information">
        <Field label="Headline">
          <input required className={inputClass} value={state.headline} onChange={(e) => set("headline", e.target.value)} />
        </Field>
        <Field label="Company">
          <select className={inputClass} value={state.company_id} onChange={(e) => set("company_id", e.target.value)}>
            <option value="">— none (industry-wide) —</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Category">
          <select className={inputClass} value={state.category} onChange={(e) => set("category", e.target.value as IntelligenceCategory)}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </Field>
      </Section>

      <Section title="Media">
        <Field label="Thumbnail URL">
          <input className={inputClass} value={state.thumbnail_url} onChange={(e) => set("thumbnail_url", e.target.value)} />
        </Field>
        <Field label="Post image URL">
          <input className={inputClass} value={state.post_image_url} onChange={(e) => set("post_image_url", e.target.value)} />
        </Field>
      </Section>

      <Section title="Content">
        <div className="sm:col-span-2">
          <Field label="Summary">
            <input className={inputClass} maxLength={500} value={state.summary} onChange={(e) => set("summary", e.target.value)} />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Field label="Full content">
            <textarea className={inputClass} rows={5} value={state.full_content} onChange={(e) => set("full_content", e.target.value)} />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Field label="Why it matters to job seekers">
            <textarea className={inputClass} rows={3} value={state.why_it_matters} onChange={(e) => set("why_it_matters", e.target.value)} />
          </Field>
          <p className="mt-1 text-xs text-muted">
            Editorial guidance (spec §12): use hedged language — &ldquo;may increase relevance of automation and
            maintenance skills&rdquo; — never an unsupported causal claim like &ldquo;this guarantees the company
            will hire engineers.&rdquo;
          </p>
        </div>
        <Field label="Relevant roles (one per line)">
          <textarea className={inputClass} rows={3} value={state.relevant_roles} onChange={(e) => set("relevant_roles", e.target.value)} />
        </Field>
        <Field label="Relevant skills (one per line)">
          <textarea className={inputClass} rows={3} value={state.relevant_skills} onChange={(e) => set("relevant_skills", e.target.value)} />
        </Field>
      </Section>

      <Section title="Source">
        <Field label="Source type">
          <select className={inputClass} value={state.source_type} onChange={(e) => set("source_type", e.target.value as SourceType)}>
            {SOURCE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </Field>
        <Field label="Original source URL">
          <input className={inputClass} value={state.source_url} onChange={(e) => set("source_url", e.target.value)} />
        </Field>
        <div className="flex items-center gap-2">
          <input id="is_verified" type="checkbox" checked={state.is_verified} onChange={(e) => set("is_verified", e.target.checked)} />
          <label htmlFor="is_verified" className="text-sm">Verified source</label>
        </div>
      </Section>

      <Section title="Publishing">
        <Field label="Status">
          <select className={inputClass} value={state.status} onChange={(e) => set("status", e.target.value as ContentStatus)}>
            {(["DRAFT", "REVIEW", "PUBLISHED", "ARCHIVED"] as ContentStatus[]).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={state.is_featured} onChange={(e) => set("is_featured", e.target.checked)} />
          Featured
        </label>
      </Section>

      {error && <p className="text-sm text-danger">{error}</p>}

      <button type="submit" disabled={saving} className="rounded-xl bg-brand px-6 py-2 text-sm font-medium text-white disabled:opacity-60">
        {saving ? "Saving..." : post ? "Save changes" : "Create intelligence post"}
      </button>
    </form>
  );
}
