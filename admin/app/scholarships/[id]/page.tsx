"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ScholarshipForm } from "@/components/ScholarshipForm";
import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { ScholarshipAdmin } from "@/types/models";

export default function EditScholarshipPage() {
  const { checked } = useAdminGuard();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [scholarship, setScholarship] = useState<ScholarshipAdmin | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    api
      .get<ScholarshipAdmin>(`/admin/scholarships/${params.id}`)
      .then(setScholarship)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load scholarship."));
  }, [checked, params.id]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-navy">{scholarship ? scholarship.name : "Edit scholarship"}</h1>
        <button onClick={() => router.push("/scholarships")} className="text-sm text-muted hover:text-ink">
          Back to scholarships
        </button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {scholarship && <ScholarshipForm scholarship={scholarship} onSaved={setScholarship} />}
    </main>
  );
}
