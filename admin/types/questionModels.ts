export type QuestionType = "SINGLE_CHOICE" | "MULTIPLE_CHOICE" | "TRUE_FALSE" | "NUMERIC" | "IMAGE_BASED" | "PASSAGE_BASED";
export type QuestionDifficulty = "EASY" | "MEDIUM" | "HARD" | "EXPERT";

export interface QuestionCategoryOut {
  id: string;
  name: string;
  slug: string;
  description: string | null;
}

export interface QuestionTopicOut {
  id: string;
  category_id: string;
  name: string;
  slug: string;
  field: string | null;
  industry: string | null;
}

export interface QuestionOptionIn {
  option_text: string | null;
  option_image_url: string | null;
  option_image_alt_text: string | null;
  is_correct: boolean;
  display_order: number;
}

export interface QuestionAdminOut {
  id: string;
  question_text: string;
  question_type: QuestionType;
  question_image_url: string | null;
  question_image_alt_text: string | null;
  category_id: string;
  topic_id: string | null;
  field: string | null;
  industry: string | null;
  job_role: string | null;
  difficulty: QuestionDifficulty;
  explanation: string | null;
  marks: number;
  negative_marks: number;
  is_active: boolean;
  options: QuestionOptionIn[];
  created_at?: string;
}

export type InterviewDifficulty = "EASY" | "MEDIUM" | "HARD" | "EXPERT";

export interface InterviewCategoryOut {
  id: string;
  name: string;
  slug: string;
  description: string | null;
}

export interface InterviewTopicOut {
  id: string;
  category_id: string;
  name: string;
  slug: string;
  field: string | null;
  industry: string | null;
}

export interface InterviewQuestionAdminOut {
  id: string;
  question_text: string;
  category_id: string;
  topic_id: string | null;
  field: string | null;
  industry: string | null;
  job_role: string | null;
  company_id: string | null;
  difficulty: InterviewDifficulty;
  evaluation_points: string[];
  follow_up_prompt: string | null;
  is_active: boolean;
  created_at?: string;
}
