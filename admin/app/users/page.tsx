"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { PaginatedResponse } from "@/types/models";

interface UserAdmin {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  applications_tracked: number;
  created_at: string;
}

export default function UsersPage() {
  const { checked } = useAdminGuard();
  const [items, setItems] = useState<UserAdmin[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const query = search ? `&search=${encodeURIComponent(search)}` : "";
      const res = await api.get<PaginatedResponse<UserAdmin>>(`/admin/users?page=1&page_size=100${query}`);
      setItems(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users.");
    }
  }

  useEffect(() => {
    if (checked) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checked]);

  async function toggleActive(user: UserAdmin) {
    const action = user.is_active ? "suspend" : "reactivate";
    if (user.is_active && !confirm(`Suspend ${user.email}? They will not be able to sign in.`)) return;
    await api.post(`/admin/users/${user.id}/${action}`);
    await load();
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-navy">Users</h1>
      <p className="mt-2 text-sm text-muted">
        Never shows OAuth tokens, password hashes, CV contents, email bodies, or interview recordings.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
        className="mt-6 flex gap-2"
      >
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by email or name..."
          className="w-72 rounded-xl border border-black/10 px-3 py-2 text-sm"
        />
        <button type="submit" className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white">
          Search
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-black/5 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Joined</th>
              <th className="px-4 py-3">Applications Tracked</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted">No users found.</td>
              </tr>
            )}
            {items.map((user) => (
              <tr key={user.id} className="border-b border-black/5 last:border-0">
                <td className="px-4 py-3">{user.full_name ?? "—"}</td>
                <td className="px-4 py-3 text-muted">{user.email}</td>
                <td className="px-4 py-3 text-muted">{new Date(user.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">{user.applications_tracked}</td>
                <td className={`px-4 py-3 ${user.is_active ? "text-success" : "text-danger"}`}>
                  {user.is_active ? "Active" : "Suspended"}
                </td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => toggleActive(user)} className={user.is_active ? "text-danger" : "text-success"}>
                    {user.is_active ? "Suspend" : "Reactivate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
