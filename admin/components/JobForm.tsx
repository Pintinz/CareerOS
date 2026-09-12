"use client";

import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/apiClient";
import {
  Company,
  ContentStatus,
  EmploymentType,
  ExperienceLevel,
  JobAdmin,
  PaginatedResponse,
  SourceType,
  WorkMode,
} from "@/types/models";

const EMPLOYMENT_TYPES: EmploymentType[] = [
  "FULL_TIME",
  "PART_TIME",
  "CONTRACT",
  "INTERNSHIP",
  "TEMPORARY",
  "VOLUNTEER",
];
const WORK_MODES: WorkMode[] = ["ON_SITE", "REMOTE", "HYBRID"];
const EXPERIENCE_LEVELS: ExperienceLevel[] = ["ENTRY", "JUNIOR", "MID", "SENIOR", "LEAD", "EXECUTIVE"];
const SOURCE_TYPES: SourceType[] = [
  "OFFICIAL_CAREER_PAGE",
  "OFFICIAL_NEWSROOM",
  "RSS",
  "LEVER",
  "ASHBY",
  "OTHER",
];

type FormState = {
  company_id: string;
  title: string;
  location: string;
  city: string;
  country: string;
  employment_type: EmploymentType;
  work_mode: WorkMode;
  experience_level: ExperienceLevel | "";
  industry: string;
  salary_min: string;
  salary_max: string;
  salary_currency: string;
  salary_period: string;
  short_summary: string;
  description: string;
  responsibilities: string;
  requirements: string;
  preferred_skills: string;
  benefits: string;
  thumbnail_url: string;
  post_image_url: string;
  image_alt_text: string;
  application_url: string;
  application_email: string;
  application_instructions: string;
  source_type: SourceType;
  source_url: string;
  application_deadline: string;
  is_verified: boolean;
  is_featured: boolean;
  is_urgent: boolean;
  status: ContentStatus;
};

const EMPTY_STATE: FormState = {
  company_id: "",
  title: "",
  location: "",
  city: "",
  country: "",
  employment_type: "FULL_TIME",
  work_mode: "ON_SITE",
  experience_level: "",
  industry: "",
  salary_min: "",
  salary_max: "",
  salary_currency: "",
  salary_period: "",
  short_summary: "",
  description: "",
  responsibilities: "",
  requirements: "",
  preferred_skills: "",
  benefits: "",
  thumbnail_url: "",
  post_image_url: "",
  image_alt_text: "",
  application_url: "",
  application_email: "",
  application_instructions: "",
  source_type: "OTHER",
  source_url: "",
  application_deadline: "",
  is_verified: false,
  is_featured: false,
  is_urgent: false,
  status: "DRAFT",
};

function jobToFormState(job: JobAdmin): FormState {
  return {
    company_id: job.company.id,
    title: job.title,
    location: job.location ?? "",
    city: job.city ?? "",
    country: job.country ?? "",
    employment_type: job.employment_type,
    work_mode: job.work_mode,
    experience_level: job.experience_level ?? "",
    industry: job.industry ?? "",
    salary_min: job.salary_min?.toString() ?? "",
    salary_max: job.salary_max?.toString() ?? "",
    salary_currency: job.salary_currency ?? "",
    salary_period: job.salary_period ?? "",
    short_summary: job.short_summary ?? "",
    description: job.description ?? "",
    responsibilities: (job.responsibilities ?? []).join("\n"),
    requirements: (job.requirements ?? []).join("\n"),
    preferred_skills: (job.preferred_skills ?? []).join("\n"),
    benefits: (job.benefits ?? []).join("\n"),
    thumbnail_url: job.thumbnail_url ?? "",
    post_image_url: job.post_image_url ?? "",
    image_alt_text: job.image_alt_text ?? "",
    application_url: job.application_url ?? "",
    application_email: job.application_email ?? "",
    application_instructions: job.application_instructions ?? "",
    source_type: job.source_type,
    source_url: job.source_url ?? "",
    application_deadline: job.application_deadline ? job.application_deadline.slice(0, 10) : "",
    is_verified: job.is_verified,
    is_featured: job.is_featured,
    is_urgent: job.is_urgent,
    status: job.status,
  };
}

function linesToList(value: string): string[] | null {
  const lines = value
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  return lines.length > 0 ? lines : null;
}

function formStateToPayload(state: FormState) {
  return {
    company_id: state.company_id,
    title: state.title,
    location: state.location || null,
    city: state.city || null,
    country: state.country || null,
    employment_type: state.employment_type,
    work_mode: state.work_mode,
    experience_level: state.experience_level || null,
    industry: state.industry || null,
    salary_min: state.salary_min ? Number(state.salary_min) : null,
    salary_max: state.salary_max ? Number(state.salary_max) : null,
    salary_currency: state.salary_currency || null,
    salary_period: state.salary_period || null,
    short_summary: state.short_summary || null,
    description: state.description || null,
    responsibilities: linesToList(state.responsibilities),
    requirements: linesToList(state.requirements),
    preferred_skills: linesToList(state.preferred_skills),
    benefits: linesToList(state.benefits),
    thumbnail_url: state.thumbnail_url || null,
    post_image_url: state.post_image_url || null,
    image_alt_text: state.image_alt_text || null,
    application_url: state.application_url || null,
    application_email: state.application_email || null,
    application_instructions: state.application_instructions || null,
    source_type: state.source_type,
    source_url: state.source_url || null,
    application_deadline: state.application_deadline
      ? new Date(state.application_deadline).toISOString()
      : null,
    is_verified: state.is_verified,
    is_featured: state.is_featured,
    is_urgent: state.is_urgent,
    status: state.status,
  };
}

const inputClass = "w-full rounded-xl border border-black/10 px-3 py-2 text-sm";
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

export function JobForm({ job, onSaved }: { job?: JobAdmin; onSaved: (job: JobAdmin) => void }) {
  const [state, setState] = useState<FormState>(job ? jobToFormState(job) : EMPTY_STATE);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<PaginatedResponse<Company>>("/admin/companies?page=1&page_size=100")
      .then((res) => setCompanies(res.items))
      .catch(() => setError("Failed to load companies. Create one first under Companies."));
  }, []);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = formStateToPayload(state);
      const saved = job
        ? await api.put<JobAdmin>(`/admin/jobs/${job.id}`, payload)
        : await api.post<JobAdmin>("/admin/jobs", payload);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save job.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Section title="Basic Information">
        <Field label="Job title">
          <input
            required
            className={inputClass}
            value={state.title}
            onChange={(e) => set("title", e.target.value)}
          />
        </Field>
        <Field label="Company">
          <select
            required
            className={inputClass}
            value={state.company_id}
            onChange={(e) => set("company_id", e.target.value)}
          >
            <option value="" disabled>
              Select a company
            </option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Location">
          <input className={inputClass} value={state.location} onChange={(e) => set("location", e.target.value)} />
        </Field>
        <Field label="Country">
          <input className={inputClass} value={state.country} onChange={(e) => set("country", e.target.value)} />
        </Field>
        <Field label="Employment type">
          <select
            className={inputClass}
            value={state.employment_type}
            onChange={(e) => set("employment_type", e.target.value as EmploymentType)}
          >
            {EMPLOYMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Work mode">
          <select
            className={inputClass}
            value={state.work_mode}
            onChange={(e) => set("work_mode", e.target.value as WorkMode)}
          >
            {WORK_MODES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Experience level">
          <select
            className={inputClass}
            value={state.experience_level}
            onChange={(e) => set("experience_level", e.target.value as ExperienceLevel | "")}
          >
            <option value="">Not specified</option>
            {EXPERIENCE_LEVELS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Industry">
          <input className={inputClass} value={state.industry} onChange={(e) => set("industry", e.target.value)} />
        </Field>
        <Field label="Salary min">
          <input
            type="number"
            className={inputClass}
            value={state.salary_min}
            onChange={(e) => set("salary_min", e.target.value)}
          />
        </Field>
        <Field label="Salary max">
          <input
            type="number"
            className={inputClass}
            value={state.salary_max}
            onChange={(e) => set("salary_max", e.target.value)}
          />
        </Field>
        <Field label="Salary currency (ISO, e.g. NGN)">
          <input
            className={inputClass}
            value={state.salary_currency}
            onChange={(e) => set("salary_currency", e.target.value)}
          />
        </Field>
        <Field label="Application deadline">
          <input
            type="date"
            className={inputClass}
            value={state.application_deadline}
            onChange={(e) => set("application_deadline", e.target.value)}
          />
        </Field>
      </Section>

      <Section title="Media">
        <Field label="Thumbnail URL">
          <input
            className={inputClass}
            value={state.thumbnail_url}
            onChange={(e) => set("thumbnail_url", e.target.value)}
          />
        </Field>
        <Field label="Post image / banner URL">
          <input
            className={inputClass}
            value={state.post_image_url}
            onChange={(e) => set("post_image_url", e.target.value)}
          />
        </Field>
        <Field label="Image alt text">
          <input
            className={inputClass}
            value={state.image_alt_text}
            onChange={(e) => set("image_alt_text", e.target.value)}
          />
        </Field>
      </Section>

      <Section title="Content">
        <div className="sm:col-span-2">
          <Field label="Short summary">
            <input
              className={inputClass}
              maxLength={500}
              value={state.short_summary}
              onChange={(e) => set("short_summary", e.target.value)}
            />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Field label="Description">
            <textarea
              className={inputClass}
              rows={5}
              value={state.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </Field>
        </div>
        <Field label="Responsibilities (one per line)">
          <textarea
            className={inputClass}
            rows={4}
            value={state.responsibilities}
            onChange={(e) => set("responsibilities", e.target.value)}
          />
        </Field>
        <Field label="Requirements (one per line)">
          <textarea
            className={inputClass}
            rows={4}
            value={state.requirements}
            onChange={(e) => set("requirements", e.target.value)}
          />
        </Field>
        <Field label="Preferred skills (one per line)">
          <textarea
            className={inputClass}
            rows={4}
            value={state.preferred_skills}
            onChange={(e) => set("preferred_skills", e.target.value)}
          />
        </Field>
        <Field label="Benefits (one per line)">
          <textarea
            className={inputClass}
            rows={4}
            value={state.benefits}
            onChange={(e) => set("benefits", e.target.value)}
          />
        </Field>
      </Section>

      <Section title="Application">
        <Field label="Official application URL">
          <input
            className={inputClass}
            value={state.application_url}
            onChange={(e) => set("application_url", e.target.value)}
          />
        </Field>
        <Field label="Application email">
          <input
            type="email"
            className={inputClass}
            value={state.application_email}
            onChange={(e) => set("application_email", e.target.value)}
          />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Application instructions">
            <textarea
              className={inputClass}
              rows={2}
              value={state.application_instructions}
              onChange={(e) => set("application_instructions", e.target.value)}
            />
          </Field>
        </div>
      </Section>

      <Section title="Source">
        <Field label="Source type">
          <select
            className={inputClass}
            value={state.source_type}
            onChange={(e) => set("source_type", e.target.value as SourceType)}
          >
            {SOURCE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Original source URL">
          <input className={inputClass} value={state.source_url} onChange={(e) => set("source_url", e.target.value)} />
        </Field>
        <div className="flex items-center gap-2">
          <input
            id="is_verified"
            type="checkbox"
            checked={state.is_verified}
            onChange={(e) => set("is_verified", e.target.checked)}
          />
          <label htmlFor="is_verified" className="text-sm">
            Verified source
          </label>
        </div>
      </Section>

      <Section title="Publishing">
        <Field label="Status">
          <select
            className={inputClass}
            value={state.status}
            onChange={(e) => set("status", e.target.value as ContentStatus)}
          >
            {(["DRAFT", "REVIEW", "PUBLISHED", "ARCHIVED"] as ContentStatus[]).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={state.is_featured}
              onChange={(e) => set("is_featured", e.target.checked)}
            />
            Featured
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={state.is_urgent} onChange={(e) => set("is_urgent", e.target.checked)} />
            Urgent
          </label>
        </div>
      </Section>

      {error && <p className="text-sm text-danger">{error}</p>}

      <button
        type="submit"
        disabled={saving}
        className="rounded-xl bg-brand px-6 py-2 text-sm font-medium text-white disabled:opacity-60"
      >
        {saving ? "Saving..." : job ? "Save changes" : "Create job"}
      </button>
    </form>
  );
}
