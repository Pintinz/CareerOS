"use client";

import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/apiClient";
import { QuestionAdminOut, QuestionCategoryOut, QuestionDifficulty, QuestionOptionIn, QuestionTopicOut, QuestionType } from "@/types/questionModels";

const QUESTION_TYPES: QuestionType[] = ["SINGLE_CHOICE", "MULTIPLE_CHOICE", "TRUE_FALSE", "NUMERIC", "IMAGE_BASED", "PASSAGE_BASED"];
const DIFFICULTIES: QuestionDifficulty[] = ["EASY", "MEDIUM", "HARD", "EXPERT"];

const inputClass = "w-full rounded-xl border border-line px-3 py-2 text-sm";
const labelClass = "mb-1 block text-xs text-muted";

function emptyOption(order: number): QuestionOptionIn {
  return { option_text: "", option_image_url: null, option_image_alt_text: null, is_correct: false, display_order: order };
}

export function AptitudeQuestionForm({ question, onSaved }: { question?: QuestionAdminOut; onSaved: (q: QuestionAdminOut) => void }) {
  const [categories, setCategories] = useState<QuestionCategoryOut[]>([]);
  const [topics, setTopics] = useState<QuestionTopicOut[]>([]);
  const [questionText, setQuestionText] = useState(question?.question_text ?? "");
  const [questionType, setQuestionType] = useState<QuestionType>(question?.question_type ?? "SINGLE_CHOICE");
  const [questionImageUrl, setQuestionImageUrl] = useState(question?.question_image_url ?? "");
  const [questionImageAlt, setQuestionImageAlt] = useState(question?.question_image_alt_text ?? "");
  const [categoryId, setCategoryId] = useState(question?.category_id ?? "");
  const [topicId, setTopicId] = useState(question?.topic_id ?? "");
  const [difficulty, setDifficulty] = useState<QuestionDifficulty>(question?.difficulty ?? "MEDIUM");
  const [explanation, setExplanation] = useState(question?.explanation ?? "");
  const [marks, setMarks] = useState(question?.marks ?? 1);
  const [negativeMarks, setNegativeMarks] = useState(question?.negative_marks ?? 0);
  const [options, setOptions] = useState<QuestionOptionIn[]>(question?.options?.length ? question.options : [emptyOption(1), emptyOption(2), emptyOption(3), emptyOption(4)]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<QuestionCategoryOut[]>("/admin/aptitude/categories").then(setCategories);
  }, []);

  useEffect(() => {
    if (categoryId) api.get<QuestionTopicOut[]>(`/admin/aptitude/topics?category_id=${categoryId}`).then(setTopics);
  }, [categoryId]);

  function updateOption(index: number, patch: Partial<QuestionOptionIn>) {
    setOptions((prev) => prev.map((o, i) => (i === index ? { ...o, ...patch } : o)));
  }

  function validate(): string | null {
    const correctCount = options.filter((o) => o.is_correct && (o.option_text || o.option_image_url)).length;
    if (questionType === "SINGLE_CHOICE" || questionType === "TRUE_FALSE") {
      if (correctCount !== 1) return `${questionType} requires exactly one correct option, found ${correctCount}.`;
    }
    if (questionType === "MULTIPLE_CHOICE" && correctCount < 1) {
      return "MULTIPLE_CHOICE requires at least one correct option.";
    }
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = {
        question_text: questionText,
        question_type: questionType,
        question_image_url: questionImageUrl || null,
        question_image_alt_text: questionImageAlt || null,
        category_id: categoryId,
        topic_id: topicId || null,
        difficulty,
        explanation: explanation || null,
        marks: Number(marks),
        negative_marks: Number(negativeMarks),
        options: options.filter((o) => o.option_text || o.option_image_url),
      };
      const saved = question
        ? await api.put<QuestionAdminOut>(`/admin/aptitude/questions/${question.id}`, payload)
        : await api.post<QuestionAdminOut>("/admin/aptitude/questions", payload);
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
        <h2 className="mb-4 text-sm font-semibold text-navy">Question</h2>
        <div className="space-y-4">
          <div>
            <label className={labelClass}>Question text</label>
            <textarea required className={inputClass} rows={3} value={questionText} onChange={(e) => setQuestionText(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Question image URL (optional — abstract/image-based questions)</label>
              <input className={inputClass} value={questionImageUrl} onChange={(e) => setQuestionImageUrl(e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Image alt text (neutral, must not reveal the answer)</label>
              <input className={inputClass} value={questionImageAlt} onChange={(e) => setQuestionImageAlt(e.target.value)} />
            </div>
          </div>
          {questionImageUrl && <img src={questionImageUrl} alt={questionImageAlt} className="h-32 rounded-lg object-contain" />}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label className={labelClass}>Type</label>
              <select className={inputClass} value={questionType} onChange={(e) => setQuestionType(e.target.value as QuestionType)}>
                {QUESTION_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
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
              <label className={labelClass}>Difficulty</label>
              <select className={inputClass} value={difficulty} onChange={(e) => setDifficulty(e.target.value as QuestionDifficulty)}>
                {DIFFICULTIES.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Marks</label>
              <input type="number" step="0.5" className={inputClass} value={marks} onChange={(e) => setMarks(Number(e.target.value))} />
            </div>
            <div>
              <label className={labelClass}>Negative marks</label>
              <input type="number" step="0.25" className={inputClass} value={negativeMarks} onChange={(e) => setNegativeMarks(Number(e.target.value))} />
            </div>
          </div>
          <div>
            <label className={labelClass}>Explanation (shown after submission)</label>
            <textarea className={inputClass} rows={2} value={explanation} onChange={(e) => setExplanation(e.target.value)} />
          </div>
        </div>
      </div>

      {questionType !== "NUMERIC" && (
        <div className="rounded-2xl bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-navy">Options</h2>
          <div className="space-y-3">
            {options.map((opt, i) => (
              <div key={i} className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={opt.is_correct}
                  onChange={(e) => updateOption(i, { is_correct: e.target.checked })}
                  title="Correct"
                />
                <input
                  className={inputClass}
                  placeholder={`Option ${i + 1} text`}
                  value={opt.option_text ?? ""}
                  onChange={(e) => updateOption(i, { option_text: e.target.value })}
                />
                <input
                  className={inputClass}
                  placeholder="Option image URL (optional)"
                  value={opt.option_image_url ?? ""}
                  onChange={(e) => updateOption(i, { option_image_url: e.target.value })}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      <button type="submit" disabled={saving} className="rounded-xl bg-brand px-6 py-2 text-sm font-medium text-white disabled:opacity-60">
        {saving ? "Saving..." : question ? "Save changes" : "Create question"}
      </button>
    </form>
  );
}
