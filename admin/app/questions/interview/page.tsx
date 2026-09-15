"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { PaginatedResponse } from "@/types/models";
import { InterviewCategoryOut, InterviewQuestionAdminOut } from "@/types/questionModels";

export default function InterviewQuestionsPage() {
  const { checked } = useAdminGuard();
  const [items, setItems] = useState<InterviewQuestionAdminOut[]>([]);
  const [categories, setCategories] = useState<InterviewCategoryOut[]>([]);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<{ imported: number; skipped: number; errors: { row: number; reason: string }[] } | null>(null);

  async function load() {
    try {
      const query = categoryFilter ? `&category_id=${categoryFilter}` : "";
      const res = await api.get<PaginatedResponse<InterviewQuestionAdminOut>>(`/admin/interview/questions?page=1&page_size=100${query}`);
      setItems(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load questions.");
    }
  }

  useEffect(() => {
    if (checked) {
      load();
      api.get<InterviewCategoryOut[]>("/admin/interview/categories").then(setCategories);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checked, categoryFilter]);

  async function handleDelete(q: InterviewQuestionAdminOut) {
    if (!confirm("Delete this question? This cannot be undone.")) return;
    await api.delete(`/admin/interview/questions/${q.id}`);
    await load();
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    const token = window.localStorage.getItem("careeros_admin_access_token");
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"}/admin/interview/questions/bulk-import`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: formData,
    });
    setImportResult(await res.json());
    await load();
    e.target.value = "";
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-navy">Interview Question Bank</h1>
        <div className="flex gap-3">
          <label className="cursor-pointer rounded-xl border border-line bg-card px-4 py-2 text-sm font-medium text-ink">
            Bulk Import CSV
            <input type="file" accept=".csv" onChange={handleImport} className="hidden" />
          </label>
          <Link href="/questions/interview/new" className="btn-primary">
            New question
          </Link>
        </div>
      </div>

      {importResult && (
        <div className="mt-4 rounded-2xl bg-card p-4 text-sm shadow-sm">
          <p>
            Imported <strong className="text-success">{importResult.imported}</strong>, skipped{" "}
            <strong>{importResult.skipped}</strong> (duplicates), <strong className="text-danger">{importResult.errors.length}</strong> errors.
          </p>
        </div>
      )}

      <div className="mt-6 flex gap-2">
        <button onClick={() => setCategoryFilter("")} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${!categoryFilter ? "bg-navy text-white" : "bg-card text-muted"}`}>
          All
        </button>
        {categories.map((c) => (
          <button
            key={c.id}
            onClick={() => setCategoryFilter(c.id)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${categoryFilter === c.id ? "bg-navy text-white" : "bg-card text-muted"}`}
          >
            {c.name}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-xs text-muted">
            <tr>
              <th className="px-4 py-3">Question</th>
              <th className="px-4 py-3">Difficulty</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Active</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted">No questions match this filter.</td>
              </tr>
            )}
            {items.map((q) => (
              <tr key={q.id} className="border-b border-line last:border-0">
                <td className="max-w-md truncate px-4 py-3 font-medium">
                  <Link href={`/questions/interview/${q.id}`} className="hover:text-brand">{q.question_text}</Link>
                </td>
                <td className="px-4 py-3 text-muted">{q.difficulty}</td>
                <td className="px-4 py-3 text-muted">{q.job_role ?? "—"}</td>
                <td className={`px-4 py-3 ${q.is_active ? "text-success" : "text-muted"}`}>{q.is_active ? "Active" : "Inactive"}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => handleDelete(q)} className="text-sm text-danger">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
