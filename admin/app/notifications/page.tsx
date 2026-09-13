"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { PaginatedResponse } from "@/types/models";

const AUDIENCES = ["ALL_USERS", "COMPANY_FOLLOWERS", "JOB_MATCH", "SCHOLARSHIP_INTERESTED", "SPECIFIC_USER"];

interface AdminNotification {
  id: string;
  title: string;
  body: string;
  audience: string;
  status: "DRAFT" | "SCHEDULED" | "SENT" | "CANCELLED";
  recipient_count: number | null;
  created_at: string;
}

export default function NotificationsPage() {
  const { checked } = useAdminGuard();
  const [items, setItems] = useState<AdminNotification[]>([]);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audience, setAudience] = useState(AUDIENCES[0]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const res = await api.get<PaginatedResponse<AdminNotification>>("/admin/notifications?page=1&page_size=100");
      setItems(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load notifications.");
    }
  }

  useEffect(() => {
    if (checked) load();
  }, [checked]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/admin/notifications", { title, body, audience });
      setTitle("");
      setBody("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create notification.");
    } finally {
      setCreating(false);
    }
  }

  async function handleSend(n: AdminNotification) {
    if (!confirm(`Send "${n.title}" now?`)) return;
    await api.post(`/admin/notifications/${n.id}/send`);
    await load();
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-navy">Notifications</h1>
      <p className="mt-2 text-sm text-muted">
        No FCM/APNs credentials are configured in this environment — sending marks a campaign SENT and records an
        honest recipient count of 0 rather than claiming a real delivery occurred. Never include private
        information in notification content.
      </p>

      <form onSubmit={handleCreate} className="mt-6 space-y-4 rounded-2xl bg-card p-6 shadow-sm">
        <div>
          <label className="mb-1 block text-xs text-muted">Title</label>
          <input required value={title} onChange={(e) => setTitle(e.target.value)} className="w-full rounded-xl border border-black/10 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Body</label>
          <textarea required value={body} onChange={(e) => setBody(e.target.value)} rows={3} className="w-full rounded-xl border border-black/10 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Audience</label>
          <select value={audience} onChange={(e) => setAudience(e.target.value)} className="w-full rounded-xl border border-black/10 px-3 py-2 text-sm">
            {AUDIENCES.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>
        {(title || body) && (
          <div className="rounded-xl bg-background p-4">
            <p className="text-xs text-muted">Preview</p>
            <p className="mt-1 text-sm font-medium">{title || "Title"}</p>
            <p className="text-sm text-muted">{body || "Body"}</p>
          </div>
        )}
        <button type="submit" disabled={creating} className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
          {creating ? "Creating..." : "Create notification"}
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 space-y-3">
        {items.map((n) => (
          <div key={n.id} className="flex items-center justify-between rounded-2xl bg-card p-4 shadow-sm">
            <div>
              <p className="font-medium">{n.title}</p>
              <p className="text-xs text-muted">{n.audience} · {n.status} {n.recipient_count !== null && `· ${n.recipient_count} recipients`}</p>
            </div>
            {n.status === "DRAFT" && (
              <button onClick={() => handleSend(n)} className="text-sm text-brand">Send now</button>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
