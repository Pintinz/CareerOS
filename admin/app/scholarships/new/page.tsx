"use client";

import { useRouter } from "next/navigation";

import { ScholarshipForm } from "@/components/ScholarshipForm";
import { useAdminGuard } from "@/components/useAdminGuard";

export default function NewScholarshipPage() {
  const { checked } = useAdminGuard();
  const router = useRouter();

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="mb-6 text-2xl font-bold text-navy">New scholarship</h1>
      <ScholarshipForm onSaved={(s) => router.push(`/scholarships/${s.id}`)} />
    </main>
  );
}
