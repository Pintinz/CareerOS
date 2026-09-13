"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { Company, PaginatedResponse } from "@/types/models";

type ItemType = "JOB" | "SCHOLARSHIP" | "INTELLIGENCE" | "ALL";

interface DiscoveredItem {
  id: string;
  source_id: string;
  item_type: "JOB" | "SCHOLARSHIP" | "INTELLIGENCE";
  detected_title: string;
  detected_company_name: string | null;
  original_url: string;
  status: "PENDING" | "REVIEWED" | "IGNORED" | "REJECTED";
  created_draft_id: string | null;
  created_at: string;
}

export default function DiscoveryPage() {
  const { checked } = useAdminGuard();
  const [tab, setTab] = useState<ItemType>("ALL");
  const [items, setItems] = useState<DiscoveredItem[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [reviewing, setReviewing] = useState<DiscoveredItem | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftCompanyId, setDraftCompanyId] = useState("");
  const [draftSummary, setDraftSummary] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const query = tab === "ALL" ? "" : `&item_type=${tab}`;
      const res = await api.get<PaginatedResponse<DiscoveredItem>>(`/admin/discovery?page=1&page_size=100${query}`);
      setItems(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load discovery queue.");
    }
  }

  useEffect(() => {
    if (checked) {
      load();
      api.get<PaginatedResponse<Company>>("/admin/companies?page=1&page_size=100").then((res) => setCompanies(res.items));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checked, tab]);

  function openReview(item: DiscoveredItem) {
    setReviewing(item);
    setDraftTitle(item.detected_title);
    setDraftCompanyId("");
    setDraftSummary("");
  }

  async function handleIgnore(item: DiscoveredItem) {
    await api.post(`/admin/discovery/${item.id}/ignore`);
    await load();
  }

  async function handleReject(item: DiscoveredItem) {
    await api.post(`/admin/discovery/${item.id}/reject`);
    await load();
  }

  async function handleCreateDraft(e: React.FormEvent) {
    e.preventDefault();
    if (!reviewing) return;
    try {
      const result = await api.post<{ item_type: string; draft_id: string }>(`/admin/discovery/${reviewing.id}/create-draft`, {
        company_id: draftCompanyId || null,
        title: draftTitle,
        summary: draftSummary || null,
      });
      setReviewing(null);
      await load();
      const dest = result.item_type === "JOB" ? "jobs" : result.item_type === "SCHOLARSHIP" ? "scholarships" : "intelligence";
      window.location.href = `/${dest}/${result.draft_id}`;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create draft.");
    }
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-bold text-navy">Discovery Queue</h1>
      <p className="mt-2 text-sm text-muted">
        Nothing here is ever auto-published — creating a draft always starts it as DRAFT, requiring a normal
        publish action afterward.
      </p>

      <div className="mt-6 flex gap-2">
        {(["ALL", "JOB", "SCHOLARSHIP", "INTELLIGENCE"] as ItemType[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold ${tab === t ? "bg-navy text-white" : "bg-card text-muted"}`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 space-y-3">
        {items.length === 0 && <p className="text-sm text-muted">No discovered items in this view.</p>}
        {items.map((item) => (
          <div key={item.id} className="flex items-center justify-between rounded-2xl bg-card p-4 shadow-sm">
            <div>
              <p className="font-medium">{item.detected_title}</p>
              <p className="text-xs text-muted">
                {item.item_type} · {item.detected_company_name ?? "Unknown company"} ·{" "}
                <a href={item.original_url} target="_blank" rel="noreferrer" className="text-brand">
                  Original source
                </a>{" "}
                · {item.status}
              </p>
            </div>
            {item.status === "PENDING" && (
              <div className="flex gap-3 text-sm">
                <button onClick={() => openReview(item)} className="text-brand">Review</button>
                <button onClick={() => handleIgnore(item)} className="text-muted">Ignore</button>
                <button onClick={() => handleReject(item)} className="text-danger">Reject</button>
              </div>
            )}
          </div>
        ))}
      </div>

      {reviewing && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/40 px-6">
          <form onSubmit={handleCreateDraft} className="w-full max-w-lg space-y-4 rounded-2xl bg-card p-6 shadow-lg">
            <h2 className="text-lg font-semibold text-navy">Review discovered item</h2>
            <p className="text-xs text-muted">
              Original: {reviewing.detected_title} —{" "}
              <a href={reviewing.original_url} target="_blank" rel="noreferrer" className="text-brand">
                source
              </a>
            </p>
            <div>
              <label className="mb-1 block text-xs text-muted">Title</label>
              <input
                required
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                className="w-full rounded-xl border border-line px-3 py-2 text-sm"
              />
            </div>
            {reviewing.item_type !== "SCHOLARSHIP" && (
              <div>
                <label className="mb-1 block text-xs text-muted">Company {reviewing.item_type === "JOB" && "(required)"}</label>
                <select
                  value={draftCompanyId}
                  onChange={(e) => setDraftCompanyId(e.target.value)}
                  className="w-full rounded-xl border border-line px-3 py-2 text-sm"
                >
                  <option value="">— select —</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label className="mb-1 block text-xs text-muted">Summary</label>
              <textarea
                value={draftSummary}
                onChange={(e) => setDraftSummary(e.target.value)}
                rows={3}
                className="w-full rounded-xl border border-line px-3 py-2 text-sm"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setReviewing(null)} className="rounded-xl px-4 py-2 text-sm text-muted">
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Create Draft
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}
