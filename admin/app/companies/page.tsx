"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { Company, PaginatedResponse } from "@/types/models";

export default function CompaniesPage() {
  const { checked } = useAdminGuard();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [industry, setIndustry] = useState("");
  const [creating, setCreating] = useState(false);

  async function loadCompanies() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<PaginatedResponse<Company>>(
        "/admin/companies?page=1&page_size=100"
      );
      setCompanies(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load companies.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (checked) loadCompanies();
  }, [checked]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await api.post("/admin/companies", {
        name,
        country: country || null,
        industry: industry || null,
      });
      setName("");
      setCountry("");
      setIndustry("");
      await loadCompanies();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create company.");
    } finally {
      setCreating(false);
    }
  }

  async function toggleVerified(company: Company) {
    await api.put(`/admin/companies/${company.id}`, { is_verified: !company.is_verified });
    await loadCompanies();
  }

  async function toggleActive(company: Company) {
    await api.put(`/admin/companies/${company.id}`, { is_active: !company.is_active });
    await loadCompanies();
  }

  async function handleDelete(company: Company) {
    if (!confirm(`Delete "${company.name}"? This cannot be undone.`)) return;
    await api.delete(`/admin/companies/${company.id}`);
    await loadCompanies();
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-navy">Companies</h1>

      <form onSubmit={handleCreate} className="mt-6 flex flex-wrap items-end gap-3 rounded-2xl bg-card p-6 shadow-sm">
        <div>
          <label className="mb-1 block text-xs text-muted">Name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-xl border border-black/10 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Country</label>
          <input
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="rounded-xl border border-black/10 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-muted">Industry</label>
          <input
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className="rounded-xl border border-black/10 px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={creating}
          className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {creating ? "Adding..." : "Add company"}
        </button>
      </form>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 overflow-x-auto rounded-2xl bg-card shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-black/5 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Country</th>
              <th className="px-4 py-3">Industry</th>
              <th className="px-4 py-3">Verified</th>
              <th className="px-4 py-3">Active</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted">
                  Loading...
                </td>
              </tr>
            )}
            {!loading && companies.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted">
                  No companies yet. Add one above.
                </td>
              </tr>
            )}
            {companies.map((company) => (
              <tr key={company.id} className="border-b border-black/5 last:border-0">
                <td className="px-4 py-3 font-medium">{company.name}</td>
                <td className="px-4 py-3 text-muted">{company.country ?? "—"}</td>
                <td className="px-4 py-3 text-muted">{company.industry ?? "—"}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggleVerified(company)}
                    className={company.is_verified ? "text-success" : "text-muted"}
                  >
                    {company.is_verified ? "Verified" : "Unverified"}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggleActive(company)}
                    className={company.is_active ? "text-success" : "text-danger"}
                  >
                    {company.is_active ? "Active" : "Inactive"}
                  </button>
                </td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => handleDelete(company)} className="text-sm text-danger">
                    Delete
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
