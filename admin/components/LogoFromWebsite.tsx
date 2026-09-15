"use client";

import { useState } from "react";

import { ApiError, api } from "@/lib/apiClient";

type CapturedLogo = { url: string; source_url: string; width: number; height: number };

/** The page to read icons from; its site root is also checked for standard icon paths. */
function pageUrlOf(value: string): string | null {
  try {
    const url = new URL(value.trim());
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

/**
 * Finds an organization's logo on its official website and stores a copy in CareerOS media
 * (never a hotlink). The result fills the form field; nothing is saved until the form is.
 */
export function LogoFromWebsite({
  websiteUrl,
  altText,
  onCaptured,
  label = "Fetch logo from website",
}: {
  websiteUrl: string;
  altText: string;
  onCaptured: (url: string) => void;
  label?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const pageUrl = pageUrlOf(websiteUrl);

  async function fetchLogo() {
    if (!pageUrl) return;
    setBusy(true);
    setMessage(null);
    try {
      const logo = await api.post<CapturedLogo>("/admin/uploads/image/from-website", { website_url: pageUrl, alt_text: altText || null });
      onCaptured(logo.url);
      setMessage({ tone: "ok", text: `Copied from ${new URL(logo.source_url).host} (${logo.width}×${logo.height}). Review it, then save.` });
    } catch (err) {
      setMessage({ tone: "error", text: err instanceof ApiError ? err.message : "Couldn't fetch a logo from that website." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button type="button" className="btn-secondary" disabled={!pageUrl || busy} onClick={fetchLogo} title={pageUrl ? `Looks for the logo on ${pageUrl}` : "Add the organization's website URL first"}>
        {busy ? "Fetching…" : label}
      </button>
      {!pageUrl && <span className="text-xs text-muted">Add the official website URL first.</span>}
      {message && <span className={`text-xs ${message.tone === "ok" ? "text-success" : "text-danger"}`}>{message.text}</span>}
    </div>
  );
}
