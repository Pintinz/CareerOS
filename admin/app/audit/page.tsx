"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { PaginatedResponse } from "@/types/models";

interface AuditLogEntry {
  id: string;
  admin_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export default function AuditPage() {
  const { checked } = useAdminGuard();
  const [items, setItems] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    api
      .get<PaginatedResponse<AuditLogEntry>>("/admin/audit?page=1&page_size=100")
      .then((res) => setItems(res.items))
      .catch((e) =>
        setError(e instanceof ApiError ? (e.status === 403 ? "Only ADMIN/SUPER_ADMIN can view audit logs." : e.message) : "Failed to load audit logs.")
      );
  }, [checked]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-bold text-navy">Audit Logs</h1>
      <p className="mt-2 text-sm text-muted">Every administrative create/update/publish/delete action, append-only. Never contains secrets.</p>
      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3">When</th>
              <th className="px-4 py-3">Admin</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Entity</th>
              <th className="px-4 py-3">Entity ID</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted">No audit entries yet.</td>
              </tr>
            )}
            {items.map((entry) => (
              <tr key={entry.id} className="border-b border-line last:border-0">
                <td className="px-4 py-3 text-muted">{new Date(entry.created_at).toLocaleString()}</td>
                <td className="px-4 py-3 font-mono text-xs text-muted">{entry.admin_id ?? "system"}</td>
                <td className="px-4 py-3 font-medium">{entry.action}</td>
                <td className="px-4 py-3">{entry.entity_type}</td>
                <td className="px-4 py-3 font-mono text-xs text-muted">{entry.entity_id ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
