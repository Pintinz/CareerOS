"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { ContentStatus, PaginatedResponse, ScholarshipAdmin } from "@/types/models";

const STATUS_FILTERS: (ContentStatus | "ALL")[] = [
  "ALL",
  "DRAFT",
  "REVIEW",
  "PUBLISHED",
  "EXPIRED",
  "ARCHIVED",
];

export default function ScholarshipsPage() {
  const { checked } = useAdminGuard();
  const [items, setItems] = useState<ScholarshipAdmin[]>([]);
  const [statusFilter, setStatusFilter] = useState<ContentStatus | "ALL">("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const query = statusFilter === "ALL" ? "" : `&status=${statusFilter}`;
      const response = await api.get<PaginatedResponse<ScholarshipAdmin>>(
        `/admin/scholarships?page=1&page_size=100${query}`
      );
      setItems(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load scholarships.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (checked) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checked, statusFilter]);

  async function setStatus(s: ScholarshipAdmin, status: ContentStatus) {
    await api.put(`/admin/scholarships/${s.id}`, { status });
    await load();
  }

  async function handleDelete(s: ScholarshipAdmin) {
    if (!confirm(`Delete "${s.name}"? This cannot be undone.`)) return;
    await api.delete(`/admin/scholarships/${s.id}`);
    await load();
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-navy">Scholarships</h1>
        <Link href="/scholarships/new" className="btn-primary">
          New scholarship
        </Link>
      </div>

      <div className="mt-6 flex gap-2">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
              statusFilter === s ? "bg-brand text-white shadow-sm" : "bg-card text-muted shadow-sm hover:text-ink"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Organization</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  Loading...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  No scholarships match this filter.
                </td>
              </tr>
            )}
            {items.map((s) => (
              <tr key={s.id} className="border-b border-line last:border-0">
                <td className="px-4 py-3 font-medium">
                  <Link href={`/scholarships/${s.id}`} className="hover:text-brand">
                    {s.name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted">{s.organization ?? "—"}</td>
                <td className="px-4 py-3">{s.status}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-3 text-xs">
                    {s.status !== "PUBLISHED" && (
                      <button onClick={() => setStatus(s, "PUBLISHED")} className="text-success">
                        Publish
                      </button>
                    )}
                    {s.status === "PUBLISHED" && (
                      <button onClick={() => setStatus(s, "DRAFT")} className="text-muted">
                        Unpublish
                      </button>
                    )}
                    <button onClick={() => handleDelete(s)} className="text-danger">
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
