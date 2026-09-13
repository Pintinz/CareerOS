"use client";

import { useEffect, useState } from "react";

import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";

interface MediaAsset {
  id: string;
  storage_key: string;
  url: string;
  mime_type: string;
  width: number | null;
  height: number | null;
  file_size: number;
  alt_text: string | null;
  created_at: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function MediaPage() {
  const { checked } = useAdminGuard();
  const [items, setItems] = useState<MediaAsset[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setItems(await api.get<MediaAsset[]>("/admin/uploads"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load media library.");
    }
  }

  useEffect(() => {
    if (checked) load();
  }, [checked]);

  async function handleDelete(asset: MediaAsset) {
    if (!confirm("Delete this asset? This cannot be undone.")) return;
    try {
      await api.delete(`/admin/uploads/${asset.id}`);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 409
            ? "This asset is referenced by existing content — replace it there first."
            : err.message
          : "Failed to delete asset."
      );
    }
  }

  function copyReference(asset: MediaAsset) {
    navigator.clipboard?.writeText(asset.url);
  }

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-navy">Media Library</h1>
      <p className="mt-2 text-sm text-muted">
        Every image uploaded through the shared admin upload pipeline — job thumbnails, scholarship banners,
        company logos, news images, and question assets. Deletion is blocked when the asset is still referenced
        by existing content.
      </p>
      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
        {items.map((asset) => (
          <div key={asset.id} className="rounded-2xl bg-card p-3 shadow-sm">
            <img src={asset.url} alt={asset.alt_text ?? ""} className="mb-2 h-32 w-full rounded-lg object-cover" />
            <p className="truncate text-xs font-medium">{asset.storage_key}</p>
            <p className="text-xs text-muted">
              {asset.mime_type} · {asset.width}×{asset.height} · {formatBytes(asset.file_size)}
            </p>
            <div className="mt-2 flex justify-between text-xs">
              <button onClick={() => copyReference(asset)} className="text-brand">Copy URL</button>
              <button onClick={() => handleDelete(asset)} className="text-danger">Delete</button>
            </div>
          </div>
        ))}
        {items.length === 0 && <p className="col-span-full text-sm text-muted">No media uploaded yet.</p>}
      </div>
    </main>
  );
}
