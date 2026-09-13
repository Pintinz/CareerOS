"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { Company, JobAdmin, IntelligencePostAdmin, PaginatedResponse } from "@/types/models";

type Tab = "overview" | "jobs" | "intelligence";

function commaList(value: string[] | null): string {
  return (value ?? []).join(", ");
}

function parseCommaList(value: string): string[] | null {
  const items = value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
  return items.length ? items : null;
}

export default function CompanyDetailPage() {
  const { checked } = useAdminGuard();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("overview");
  const [company, setCompany] = useState<Company | null>(null);
  const [jobs, setJobs] = useState<JobAdmin[]>([]);
  const [posts, setPosts] = useState<IntelligencePostAdmin[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    name: "", logoUrl: "", bannerUrl: "", websiteUrl: "", careerUrl: "", industry: "",
    headquarters: "", country: "", description: "", knownTechnologies: "", businessAreas: "", locations: "",
  });

  useEffect(() => {
    if (!checked) return;
    api.get<Company>(`/admin/companies/${id}`).then((c) => {
      setCompany(c);
      setForm({
        name: c.name, logoUrl: c.logo_url ?? "", bannerUrl: c.banner_url ?? "", websiteUrl: c.website_url ?? "",
        careerUrl: c.career_url ?? "", industry: c.industry ?? "", headquarters: c.headquarters ?? "",
        country: c.country ?? "", description: c.description ?? "", knownTechnologies: commaList(c.known_technologies),
        businessAreas: commaList(c.business_areas), locations: commaList(c.locations),
      });
    });
  }, [checked, id]);

  useEffect(() => {
    if (!checked || tab !== "jobs") return;
    api.get<PaginatedResponse<JobAdmin>>(`/admin/jobs?page=1&page_size=50`).then((res) => {
      setJobs(res.items.filter((j) => j.company.id === id));
    });
  }, [checked, tab, id]);

  useEffect(() => {
    if (!checked || tab !== "intelligence") return;
    api.get<PaginatedResponse<IntelligencePostAdmin>>(`/admin/intelligence?page=1&page_size=50`).then((res) => {
      setPosts(res.items.filter((p) => p.company?.id === id));
    });
  }, [checked, tab, id]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.put(`/admin/companies/${id}`, {
        name: form.name,
        logo_url: form.logoUrl || null,
        banner_url: form.bannerUrl || null,
        website_url: form.websiteUrl || null,
        career_url: form.careerUrl || null,
        industry: form.industry || null,
        headquarters: form.headquarters || null,
        country: form.country || null,
        description: form.description || null,
        known_technologies: parseCommaList(form.knownTechnologies),
        business_areas: parseCommaList(form.businessAreas),
        locations: parseCommaList(form.locations),
      });
      router.push("/companies");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save company.");
    } finally {
      setSaving(false);
    }
  }

  if (!checked || !company) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-bold text-navy">{company.name}</h1>

      <div className="mt-6 flex gap-2 border-b border-line">
        {(["overview", "jobs", "intelligence"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm capitalize ${tab === t ? "border-b-2 border-brand font-medium text-brand" : "text-muted"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <form onSubmit={handleSave} className="mt-6 space-y-4 rounded-2xl bg-card p-6 shadow-sm">
          {error && <p className="text-sm text-danger">{error}</p>}
          <Field label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} required />
          <div className="grid grid-cols-2 gap-4">
            <Field label="Logo URL" value={form.logoUrl} onChange={(v) => setForm({ ...form, logoUrl: v })} />
            <Field label="Banner URL" value={form.bannerUrl} onChange={(v) => setForm({ ...form, bannerUrl: v })} />
          </div>
          {form.logoUrl && <img src={form.logoUrl} alt="Logo preview" className="h-16 w-16 rounded-lg object-cover" />}
          <div className="grid grid-cols-2 gap-4">
            <Field label="Website URL" value={form.websiteUrl} onChange={(v) => setForm({ ...form, websiteUrl: v })} />
            <Field label="Career Page URL" value={form.careerUrl} onChange={(v) => setForm({ ...form, careerUrl: v })} />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Industry" value={form.industry} onChange={(v) => setForm({ ...form, industry: v })} />
            <Field label="Headquarters" value={form.headquarters} onChange={(v) => setForm({ ...form, headquarters: v })} />
            <Field label="Country" value={form.country} onChange={(v) => setForm({ ...form, country: v })} />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={4}
              className="w-full rounded-xl border border-line px-3 py-2 text-sm"
            />
          </div>
          <p className="text-xs text-muted">
            Structured intelligence fields — editorially entered facts only, never inferred (comma-separated).
          </p>
          <Field label="Known Technologies" value={form.knownTechnologies} onChange={(v) => setForm({ ...form, knownTechnologies: v })} />
          <Field label="Business Areas" value={form.businessAreas} onChange={(v) => setForm({ ...form, businessAreas: v })} />
          <Field label="Locations" value={form.locations} onChange={(v) => setForm({ ...form, locations: v })} />

          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </form>
      )}

      {tab === "jobs" && (
        <div className="mt-6 space-y-3">
          <a href={`/jobs/new`} className="inline-block rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white">
            + Job for this company
          </a>
          {jobs.length === 0 && <p className="text-sm text-muted">No jobs for this company yet.</p>}
          {jobs.map((job) => (
            <div key={job.id} className="rounded-2xl bg-card p-4 shadow-sm">
              <a href={`/jobs/${job.id}`} className="font-medium text-brand">
                {job.title}
              </a>
            </div>
          ))}
        </div>
      )}

      {tab === "intelligence" && (
        <div className="mt-6 space-y-3">
          <a href={`/intelligence/new`} className="inline-block rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white">
            + Intelligence post for this company
          </a>
          {posts.length === 0 && <p className="text-sm text-muted">No intelligence posts for this company yet.</p>}
          {posts.map((post) => (
            <div key={post.id} className="rounded-2xl bg-card p-4 shadow-sm">
              <a href={`/intelligence/${post.id}`} className="font-medium text-brand">
                {post.headline}
              </a>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

function Field({
  label, value, onChange, required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs text-muted">{label}</label>
      <input
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-line px-3 py-2 text-sm"
      />
    </div>
  );
}
