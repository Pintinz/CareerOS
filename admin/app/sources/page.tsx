"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";

const SOURCE_TYPES = [
  "OFFICIAL_CAREER_PAGE", "OFFICIAL_NEWSROOM", "INVESTOR_RELATIONS", "RSS", "LEVER", "ASHBY",
  "UNIVERSITY", "SCHOLARSHIP_PROVIDER", "GOVERNMENT", "REGULATOR", "INDUSTRY_PUBLICATION", "OTHER",
];

interface ContentSource {
  id: string;
  name: string;
  organization: string | null;
  url: string;
  source_type: string;
  is_active: boolean;
  verification_status: "UNVERIFIED" | "VERIFIED" | "FAILING";
  last_checked_at: string | null;
  last_successful_fetch_at: string | null;
  last_error: string | null;
}

export default function SourcesPage() {
  const { checked } = useAdminGuard();
  const [items, setItems] = useState<ContentSource[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] = useState(SOURCE_TYPES[0]);
  const [creating, setCreating] = useState(false);

  async function load() {
    try {
      setItems(await api.get<ContentSource[]>("/admin/sources"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load sources.");
    }
  }

  useEffect(() => {
    if (checked) load();
  }, [checked]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/admin/sources", { name, url, source_type: sourceType });
      setName("");
      setUrl("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create source.");
    } finally {
      setCreating(false);
    }
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-navy">Content Sources</h1>
      <p className="mt-2 text-sm text-muted">
        The registry of places CareerOS could track for new jobs/scholarships/intelligence. Registering a source
        here does not by itself ingest anything — no live RSS/Lever/Ashby polling adapter is wired up in this
        environment yet; use Discovery&rsquo;s manual entry point, or a future ingestion worker, to populate items
        against a source.
      </p>

      <form onSubmit={handleCreate} className="mt-6 flex flex-wrap items-end gap-3 rounded-2xl bg-card p-6 shadow-sm">
        <div>
          <label className="mb-1 block text-xs text-muted">Name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} className="rounded-xl border border-black/10 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">URL</label>
          <input required value={url} onChange={(e) => setUrl(e.target.value)} className="w-64 rounded-xl border border-black/10 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Type</label>
          <select value={sourceType} onChange={(e) => setSourceType(e.target.value)} className="rounded-xl border border-black/10 px-3 py-2 text-sm">
            {SOURCE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <button type="submit" disabled={creating} className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
          {creating ? "Adding..." : "Add source"}
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-black/5 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Verification</th>
              <th className="px-4 py-3">Last Checked</th>
              <th className="px-4 py-3">Last Error</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted">No sources registered yet.</td>
              </tr>
            )}
            {items.map((s) => (
              <tr key={s.id} className="border-b border-black/5 last:border-0">
                <td className="px-4 py-3 font-medium">{s.name}</td>
                <td className="px-4 py-3 text-muted">{s.source_type}</td>
                <td className="px-4 py-3">{s.verification_status}</td>
                <td className="px-4 py-3 text-muted">{s.last_checked_at ? new Date(s.last_checked_at).toLocaleString() : "Never"}</td>
                <td className="px-4 py-3 text-danger">{s.last_error ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
