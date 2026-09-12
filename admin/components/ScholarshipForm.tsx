"use client";

import { useState } from "react";

import { ApiError, api } from "@/lib/apiClient";
import { ContentStatus, DegreeLevel, FundingType, ScholarshipAdmin, SourceType } from "@/types/models";

const DEGREE_LEVELS: DegreeLevel[] = ["UNDERGRADUATE", "MASTERS", "PHD", "OTHER"];
const FUNDING_TYPES: FundingType[] = ["FULLY_FUNDED", "PARTIAL"];
const SOURCE_TYPES: SourceType[] = [
  "OFFICIAL_CAREER_PAGE",
  "OFFICIAL_NEWSROOM",
  "RSS",
  "LEVER",
  "ASHBY",
  "OTHER",
];

type FormState = {
  name: string;
  organization: string;
  country: string;
  degree_levels: DegreeLevel[];
  fields_of_study: string;
  funding_type: FundingType;
  tuition_coverage: string;
  monthly_stipend: string;
  travel_support: string;
  insurance_support: string;
  accommodation_support: string;
  summary: string;
  description: string;
  eligible_nationalities: string;
  academic_requirements: string;
  language_requirements: string;
  required_documents: string;
  thumbnail_url: string;
  official_url: string;
  source_type: SourceType;
  source_url: string;
  application_deadline: string;
  is_verified: boolean;
  is_featured: boolean;
  status: ContentStatus;
};

const EMPTY_STATE: FormState = {
  name: "",
  organization: "",
  country: "",
  degree_levels: [],
  fields_of_study: "",
  funding_type: "PARTIAL",
  tuition_coverage: "",
  monthly_stipend: "",
  travel_support: "",
  insurance_support: "",
  accommodation_support: "",
  summary: "",
  description: "",
  eligible_nationalities: "",
  academic_requirements: "",
  language_requirements: "",
  required_documents: "",
  thumbnail_url: "",
  official_url: "",
  source_type: "OTHER",
  source_url: "",
  application_deadline: "",
  is_verified: false,
  is_featured: false,
  status: "DRAFT",
};

function scholarshipToFormState(s: ScholarshipAdmin): FormState {
  return {
    name: s.name,
    organization: s.organization ?? "",
    country: s.country ?? "",
    degree_levels: s.degree_levels ?? [],
    fields_of_study: (s.fields_of_study ?? []).join("\n"),
    funding_type: s.funding_type,
    tuition_coverage: s.tuition_coverage ?? "",
    monthly_stipend: s.monthly_stipend ?? "",
    travel_support: s.travel_support ?? "",
    insurance_support: s.insurance_support ?? "",
    accommodation_support: s.accommodation_support ?? "",
    summary: s.summary ?? "",
    description: s.description ?? "",
    eligible_nationalities: (s.eligible_nationalities ?? []).join("\n"),
    academic_requirements: (s.academic_requirements ?? []).join("\n"),
    language_requirements: (s.language_requirements ?? []).join("\n"),
    required_documents: (s.required_documents ?? []).join("\n"),
    thumbnail_url: s.thumbnail_url ?? "",
    official_url: s.official_url ?? "",
    source_type: s.source_type,
    source_url: s.source_url ?? "",
    application_deadline: s.application_deadline ? s.application_deadline.slice(0, 10) : "",
    is_verified: s.is_verified,
    is_featured: s.is_featured,
    status: s.status,
  };
}

function linesToList(value: string): string[] | null {
  const lines = value.split("\n").map((l) => l.trim()).filter(Boolean);
  return lines.length > 0 ? lines : null;
}

function formStateToPayload(state: FormState) {
  return {
    name: state.name,
    organization: state.organization || null,
    country: state.country || null,
    degree_levels: state.degree_levels.length > 0 ? state.degree_levels : null,
    fields_of_study: linesToList(state.fields_of_study),
    funding_type: state.funding_type,
    tuition_coverage: state.tuition_coverage || null,
    monthly_stipend: state.monthly_stipend || null,
    travel_support: state.travel_support || null,
    insurance_support: state.insurance_support || null,
    accommodation_support: state.accommodation_support || null,
    summary: state.summary || null,
    description: state.description || null,
    eligible_nationalities: linesToList(state.eligible_nationalities),
    academic_requirements: linesToList(state.academic_requirements),
    language_requirements: linesToList(state.language_requirements),
    required_documents: linesToList(state.required_documents),
    thumbnail_url: state.thumbnail_url || null,
    official_url: state.official_url || null,
    source_type: state.source_type,
    source_url: state.source_url || null,
    application_deadline: state.application_deadline
      ? new Date(state.application_deadline).toISOString()
      : null,
    is_verified: state.is_verified,
    is_featured: state.is_featured,
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

export function ScholarshipForm({
  scholarship,
  onSaved,
}: {
  scholarship?: ScholarshipAdmin;
  onSaved: (s: ScholarshipAdmin) => void;
}) {
  const [state, setState] = useState<FormState>(
    scholarship ? scholarshipToFormState(scholarship) : EMPTY_STATE
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((prev) => ({ ...prev, [key]: value }));
  }

  function toggleDegreeLevel(level: DegreeLevel) {
    setState((prev) => ({
      ...prev,
      degree_levels: prev.degree_levels.includes(level)
        ? prev.degree_levels.filter((l) => l !== level)
        : [...prev.degree_levels, level],
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = formStateToPayload(state);
      const saved = scholarship
        ? await api.put<ScholarshipAdmin>(`/admin/scholarships/${scholarship.id}`, payload)
        : await api.post<ScholarshipAdmin>("/admin/scholarships", payload);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save scholarship.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Section title="Basic Information">
        <Field label="Scholarship name">
          <input required className={inputClass} value={state.name} onChange={(e) => set("name", e.target.value)} />
        </Field>
        <Field label="Organization">
          <input
            className={inputClass}
            value={state.organization}
            onChange={(e) => set("organization", e.target.value)}
          />
        </Field>
        <Field label="Country">
          <input className={inputClass} value={state.country} onChange={(e) => set("country", e.target.value)} />
        </Field>
        <Field label="Funding type">
          <select
            className={inputClass}
            value={state.funding_type}
            onChange={(e) => set("funding_type", e.target.value as FundingType)}
          >
            {FUNDING_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <div className="sm:col-span-2">
          <label className={labelClass}>Degree levels</label>
          <div className="flex flex-wrap gap-3">
            {DEGREE_LEVELS.map((level) => (
              <label key={level} className="flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  checked={state.degree_levels.includes(level)}
                  onChange={() => toggleDegreeLevel(level)}
                />
                {level}
              </label>
            ))}
          </div>
        </div>
        <Field label="Application deadline">
          <input
            type="date"
            className={inputClass}
            value={state.application_deadline}
            onChange={(e) => set("application_deadline", e.target.value)}
          />
        </Field>
        <Field label="Fields of study (one per line)">
          <textarea
            className={inputClass}
            rows={3}
            value={state.fields_of_study}
            onChange={(e) => set("fields_of_study", e.target.value)}
          />
        </Field>
      </Section>

      <Section title="Funding coverage">
        <Field label="Tuition coverage">
          <input
            className={inputClass}
            value={state.tuition_coverage}
            onChange={(e) => set("tuition_coverage", e.target.value)}
          />
        </Field>
        <Field label="Monthly stipend">
          <input
            className={inputClass}
            value={state.monthly_stipend}
            onChange={(e) => set("monthly_stipend", e.target.value)}
          />
        </Field>
        <Field label="Travel support">
          <input
            className={inputClass}
            value={state.travel_support}
            onChange={(e) => set("travel_support", e.target.value)}
          />
        </Field>
        <Field label="Insurance support">
          <input
            className={inputClass}
            value={state.insurance_support}
            onChange={(e) => set("insurance_support", e.target.value)}
          />
        </Field>
        <Field label="Accommodation support">
          <input
            className={inputClass}
            value={state.accommodation_support}
            onChange={(e) => set("accommodation_support", e.target.value)}
          />
        </Field>
      </Section>

      <Section title="Content">
        <div className="sm:col-span-2">
          <Field label="Summary">
            <input
              className={inputClass}
              maxLength={500}
              value={state.summary}
              onChange={(e) => set("summary", e.target.value)}
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
      </Section>

      <Section title="Eligibility">
        <Field label="Eligible nationalities (one per line)">
          <textarea
            className={inputClass}
            rows={3}
            value={state.eligible_nationalities}
            onChange={(e) => set("eligible_nationalities", e.target.value)}
          />
        </Field>
        <Field label="Academic requirements (one per line)">
          <textarea
            className={inputClass}
            rows={3}
            value={state.academic_requirements}
            onChange={(e) => set("academic_requirements", e.target.value)}
          />
        </Field>
        <Field label="Language requirements (one per line)">
          <textarea
            className={inputClass}
            rows={3}
            value={state.language_requirements}
            onChange={(e) => set("language_requirements", e.target.value)}
          />
        </Field>
        <Field label="Required documents (one per line)">
          <textarea
            className={inputClass}
            rows={3}
            value={state.required_documents}
            onChange={(e) => set("required_documents", e.target.value)}
          />
        </Field>
      </Section>

      <Section title="Media & Source">
        <Field label="Thumbnail URL">
          <input
            className={inputClass}
            value={state.thumbnail_url}
            onChange={(e) => set("thumbnail_url", e.target.value)}
          />
        </Field>
        <Field label="Official application URL">
          <input
            className={inputClass}
            value={state.official_url}
            onChange={(e) => set("official_url", e.target.value)}
          />
        </Field>
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
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={state.is_featured} onChange={(e) => set("is_featured", e.target.checked)} />
          Featured
        </label>
      </Section>

      {error && <p className="text-sm text-danger">{error}</p>}

      <button
        type="submit"
        disabled={saving}
        className="rounded-xl bg-brand px-6 py-2 text-sm font-medium text-white disabled:opacity-60"
      >
        {saving ? "Saving..." : scholarship ? "Save changes" : "Create scholarship"}
      </button>
    </form>
  );
}
