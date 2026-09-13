"use client";

import { useRouter } from "next/navigation";

import { InterviewQuestionForm } from "@/components/InterviewQuestionForm";
import { useAdminGuard } from "@/components/useAdminGuard";

export default function NewInterviewQuestionPage() {
  const { checked } = useAdminGuard();
  const router = useRouter();

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-6 text-2xl font-bold text-navy">New interview question</h1>
      <InterviewQuestionForm onSaved={(q) => router.push(`/questions/interview/${q.id}`)} />
    </main>
  );
}
