"use client";

import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/apiClient";
import { InterviewCategoryOut, InterviewDifficulty, InterviewQuestionAdminOut, InterviewTopicOut } from "@/types/questionModels";

const DIFFICULTIES: InterviewDifficulty[] = ["EASY", "MEDIUM", "HARD", "EXPERT"];
const inputClass = "w-full rounded-xl border border-black/10 px-3 py-2 text-sm";
const labelClass = "mb-1 block text-xs text-muted";

export function InterviewQuestionForm({
  question, onSaved,
}: {
  question?: InterviewQuestionAdminOut;
  onSaved: (q: InterviewQuestionAdminOut) => void;
}) {
  const [categories, setCategories] = useState<InterviewCategoryOut[]>([]);
  const [topics, setTopics] = useState<InterviewTopicOut[]>([]);
  const [questionText, setQuestionText] = useState(question?.question_text ?? "");
  const [categoryId, setCategoryId] = useState(question?.category_id ?? "");
  const [topicId, setTopicId] = useState(question?.topic_id ?? "");
  const [jobRole, setJobRole] = useState(question?.job_role ?? "");
  const [industry, setIndustry] = useState(question?.industry ?? "");
  const [difficulty, setDifficulty] = useState<InterviewDifficulty>(question?.difficulty ?? "MEDIUM");
  const [evaluationPoints, setEvaluationPoints] = useState((question?.evaluation_points ?? []).join("\n"));
  const [followUpPrompt, setFollowUpPrompt] = useState(question?.follow_up_prompt ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<InterviewCategoryOut[]>("/admin/interview/categories").then(setCategories);
  }, []);

  useEffect(() => {
    if (categoryId) api.get<InterviewTopicOut[]>(`/admin/interview/topics?category_id=${categoryId}`).then(setTopics);
  }, [categoryId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        question_text: questionText,
        category_id: categoryId,
        topic_id: topicId || null,
        job_role: jobRole || null,
        industry: industry || null,
        difficulty,
        evaluation_points: evaluationPoints.split("\n").map((l) => l.trim()).filter(Boolean),
        follow_up_prompt: followUpPrompt || null,
      };
      const saved = question
        ? await api.put<InterviewQuestionAdminOut>(`/admin/interview/questions/${question.id}`, payload)
        : await api.post<InterviewQuestionAdminOut>("/admin/interview/questions", payload);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save question.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="rounded-2xl bg-card p-6 shadow-sm">
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Question</label>
            <textarea required className={inputClass} rows={3} value={questionText} onChange={(e) => setQuestionText(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label className={labelClass}>Category</label>
              <select required className={inputClass} value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">— select —</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Topic</label>
              <select className={inputClass} value={topicId} onChange={(e) => setTopicId(e.target.value)}>
                <option value="">— none —</option>
                {topics.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Role</label>
              <input className={inputClass} value={jobRole} onChange={(e) => setJobRole(e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Industry</label>
              <input className={inputClass} value={industry} onChange={(e) => setIndustry(e.target.value)} />
            </div>
          </div>
          <div>
            <label className={labelClass}>Difficulty</label>
            <select className={inputClass} value={difficulty} onChange={(e) => setDifficulty(e.target.value as InterviewDifficulty)}>
              {DIFFICULTIES.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Evaluation points (one per line)</label>
            <textarea className={inputClass} rows={3} value={evaluationPoints} onChange={(e) => setEvaluationPoints(e.target.value)} />
          </div>
          <div>
            <label className={labelClass}>Follow-up prompt</label>
            <input className={inputClass} value={followUpPrompt} onChange={(e) => setFollowUpPrompt(e.target.value)} />
          </div>
        </div>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <button type="submit" disabled={saving} className="rounded-xl bg-brand px-6 py-2 text-sm font-medium text-white disabled:opacity-60">
        {saving ? "Saving..." : question ? "Save changes" : "Create question"}
      </button>
    </form>
  );
}
