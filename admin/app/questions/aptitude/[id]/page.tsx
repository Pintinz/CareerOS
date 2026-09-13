"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AptitudeQuestionForm } from "@/components/AptitudeQuestionForm";
import { useAdminGuard } from "@/components/useAdminGuard";
import { ApiError, api } from "@/lib/apiClient";
import { QuestionAdminOut } from "@/types/questionModels";

export default function EditAptitudeQuestionPage() {
  const { checked } = useAdminGuard();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [question, setQuestion] = useState<QuestionAdminOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!checked) return;
    api
      .get<QuestionAdminOut>(`/admin/aptitude/questions/${params.id}`)
      .then(setQuestion)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load question."));
  }, [checked, params.id]);

  if (!checked) return null;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-navy">Edit question</h1>
        <button onClick={() => router.push("/questions/aptitude")} className="text-sm text-muted hover:text-ink">
          Back to question bank
        </button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {question && <AptitudeQuestionForm question={question} onSaved={setQuestion} />}
    </main>
  );
}
