"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { IntelligenceForm } from "@/components/IntelligenceForm";
import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { IntelligencePostAdmin } from "@/types/models";

export default function EditIntelligencePage() {
  const { checked } = useAdminGuard();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [post, setPost] = useState<IntelligencePostAdmin | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    api
      .get<IntelligencePostAdmin>(`/admin/intelligence/${params.id}`)
      .then(setPost)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load intelligence post."));
  }, [checked, params.id]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-navy">{post ? post.headline : "Edit intelligence post"}</h1>
        <button onClick={() => router.push("/intelligence")} className="text-sm text-muted hover:text-ink">
          Back to intelligence
        </button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {post && <IntelligenceForm post={post} onSaved={setPost} />}
    </main>
  );
}
