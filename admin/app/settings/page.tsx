"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";

interface Setting {
  key: string;
  value: Record<string, number>;
  description: string | null;
  updated_at: string | null;
  is_default: boolean;
}

export default function SettingsPage() {
  const { checked } = useAdminGuard();
  const [settings, setSettings] = useState<Record<string, Setting> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  async function load() {
    try {
      const data = await api.get<Record<string, Setting>>("/admin/settings");
      setSettings(data);
      const nextDrafts: Record<string, string> = {};
      Object.entries(data).forEach(([key, s]) => {
        nextDrafts[key] = JSON.stringify(s.value, null, 2);
      });
      setDrafts(nextDrafts);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 403
            ? "Only SUPER_ADMIN can view or change system settings."
            : err.message
          : "Failed to load settings."
      );
    }
  }

  useEffect(() => {
    if (checked) load();
  }, [checked]);

  async function save(key: string) {
    setSavingKey(key);
    setError(null);
    try {
      const value = JSON.parse(drafts[key]);
      await api.put(`/admin/settings/${key}`, { value });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Invalid JSON value.");
    } finally {
      setSavingKey(null);
    }
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-bold text-navy">System Settings</h1>
      <p className="mt-2 text-sm text-muted">
        Non-secret, runtime-configurable values (scoring weights, matching thresholds, classifier confidence
        cutoffs). Secret API keys always remain in environment/secret management, never here.
      </p>
      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      {settings && (
        <div className="mt-6 space-y-4">
          {Object.entries(settings).map(([key, s]) => (
            <div key={key} className="rounded-2xl bg-card p-6 shadow-sm">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="font-mono text-sm font-semibold text-navy">{key}</h2>
                {s.is_default && <span className="rounded-full bg-muted/10 px-2 py-0.5 text-xs text-muted">Default (unmodified)</span>}
              </div>
              <p className="mb-3 text-xs text-muted">{s.description}</p>
              <textarea
                className="w-full rounded-xl border border-line px-3 py-2 font-mono text-xs"
                rows={4}
                value={drafts[key] ?? ""}
                onChange={(e) => setDrafts({ ...drafts, [key]: e.target.value })}
              />
              <button
                onClick={() => save(key)}
                disabled={savingKey === key}
                className="mt-3 rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
              >
                {savingKey === key ? "Saving..." : "Save"}
              </button>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
