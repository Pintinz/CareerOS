"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { JobForm } from "@/components/JobForm";
import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { JobAdmin } from "@/types/models";

export default function EditJobPage() {
  const { checked } = useAdminGuard();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<JobAdmin | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    api
      .get<JobAdmin>(`/admin/jobs/${params.id}`)
      .then(setJob)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load job."));
  }, [checked, params.id]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-navy">{job ? job.title : "Edit job"}</h1>
        <button onClick={() => router.push("/jobs")} className="text-sm text-muted hover:text-ink">
          Back to jobs
        </button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {job && <JobForm job={job} onSaved={setJob} />}
    </main>
  );
}
