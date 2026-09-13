"use client";

import { useRouter } from "next/navigation";

import { JobForm } from "@/components/JobForm";
import { useAdminGuard } from "@/components/useAdminGuard";

export default function NewJobPage() {
  const { checked } = useAdminGuard();
  const router = useRouter();

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="mb-6 text-2xl font-bold text-navy">New job</h1>
      <JobForm onSaved={(job) => router.push(`/jobs/${job.id}`)} />
    </main>
  );
}
