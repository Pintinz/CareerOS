"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { ContentStatus, JobAdmin, PaginatedResponse } from "@/types/models";

const STATUS_FILTERS: (ContentStatus | "ALL")[] = [
  "ALL",
  "DRAFT",
  "REVIEW",
  "PUBLISHED",
  "EXPIRED",
  "ARCHIVED",
];

const STATUS_COLORS: Record<ContentStatus, string> = {
  DRAFT: "bg-muted/10 text-muted",
  REVIEW: "bg-warning/10 text-warning",
  PUBLISHED: "bg-success/10 text-success",
  EXPIRED: "bg-danger/10 text-danger",
  ARCHIVED: "bg-muted/10 text-muted",
};

export default function JobsPage() {
  const { checked } = useAdminGuard();
  const [jobs, setJobs] = useState<JobAdmin[]>([]);
  const [statusFilter, setStatusFilter] = useState<ContentStatus | "ALL">("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadJobs() {
    setLoading(true);
    setError(null);
    try {
      const query = statusFilter === "ALL" ? "" : `&status=${statusFilter}`;
      const response = await api.get<PaginatedResponse<JobAdmin>>(
        `/admin/jobs?page=1&page_size=100${query}`
      );
      setJobs(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load jobs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (checked) loadJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checked, statusFilter]);

  async function setStatus(job: JobAdmin, status: ContentStatus) {
    await api.put(`/admin/jobs/${job.id}`, { status });
    await loadJobs();
  }

  async function toggleFlag(job: JobAdmin, flag: "is_featured" | "is_urgent") {
    await api.put(`/admin/jobs/${job.id}`, { [flag]: !job[flag] });
    await loadJobs();
  }

  async function handleDuplicate(job: JobAdmin) {
    await api.post(`/admin/jobs/${job.id}/duplicate`);
    await loadJobs();
  }

  async function handleDelete(job: JobAdmin) {
    if (!confirm(`Delete "${job.title}"? This cannot be undone.`)) return;
    await api.delete(`/admin/jobs/${job.id}`);
    await loadJobs();
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-navy">Jobs</h1>
        <Link
          href="/jobs/new"
          className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white"
        >
          New job
        </Link>
      </div>

      <div className="mt-6 flex gap-2">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              statusFilter === s ? "bg-navy text-white" : "bg-card text-muted"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-black/5 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Flags</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted">
                  Loading...
                </td>
              </tr>
            )}
            {!loading && jobs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted">
                  No jobs match this filter.
                </td>
              </tr>
            )}
            {jobs.map((job) => (
              <tr key={job.id} className="border-b border-black/5 last:border-0 align-top">
                <td className="px-4 py-3 font-medium">
                  <Link href={`/jobs/${job.id}`} className="hover:text-brand">
                    {job.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted">{job.company.name}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2 py-1 text-xs font-medium ${STATUS_COLORS[job.status]}`}>
                    {job.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2 text-xs">
                    <button
                      onClick={() => toggleFlag(job, "is_featured")}
                      className={job.is_featured ? "text-brand" : "text-muted"}
                    >
                      {job.is_featured ? "★ Featured" : "☆ Feature"}
                    </button>
                    <button
                      onClick={() => toggleFlag(job, "is_urgent")}
                      className={job.is_urgent ? "text-danger" : "text-muted"}
                    >
                      {job.is_urgent ? "Urgent" : "Mark urgent"}
                    </button>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap justify-end gap-3 text-xs">
                    {job.status !== "PUBLISHED" && (
                      <button onClick={() => setStatus(job, "PUBLISHED")} className="text-success">
                        Publish
                      </button>
                    )}
                    {job.status === "PUBLISHED" && (
                      <button onClick={() => setStatus(job, "DRAFT")} className="text-muted">
                        Unpublish
                      </button>
                    )}
                    {job.status !== "ARCHIVED" && (
                      <button onClick={() => setStatus(job, "ARCHIVED")} className="text-muted">
                        Archive
                      </button>
                    )}
                    <button onClick={() => handleDuplicate(job)} className="text-muted">
                      Duplicate
                    </button>
                    <button onClick={() => handleDelete(job)} className="text-danger">
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
