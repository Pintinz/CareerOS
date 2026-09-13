"use client";

import { useRouter } from "next/navigation";

import { AptitudeQuestionForm } from "@/components/AptitudeQuestionForm";
import { useAdminGuard } from "@/components/useAdminGuard";

export default function NewAptitudeQuestionPage() {
  const { checked } = useAdminGuard();
  const router = useRouter();

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-6 text-2xl font-bold text-navy">New aptitude question</h1>
      <AptitudeQuestionForm onSaved={(q) => router.push(`/questions/aptitude/${q.id}`)} />
    </main>
  );
}
