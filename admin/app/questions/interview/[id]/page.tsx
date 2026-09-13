"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { InterviewQuestionForm } from "@/components/InterviewQuestionForm";
import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { InterviewQuestionAdminOut } from "@/types/questionModels";

export default function EditInterviewQuestionPage() {
  const { checked } = useAdminGuard();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [question, setQuestion] = useState<InterviewQuestionAdminOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    api
      .get<InterviewQuestionAdminOut>(`/admin/interview/questions/${params.id}`)
      .then(setQuestion)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load question."));
  }, [checked, params.id]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-navy">Edit question</h1>
        <button onClick={() => router.push("/questions/interview")} className="text-sm text-muted hover:text-ink">
          Back to question bank
        </button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {question && <InterviewQuestionForm question={question} onSaved={setQuestion} />}
    </main>
  );
}
