export interface Company {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  banner_url: string | null;
  website_url: string | null;
  career_url: string | null;
  industry: string | null;
  headquarters: string | null;
  country: string | null;
  description: string | null;
  known_technologies: string[] | null;
  business_areas: string[] | null;
  locations: string[] | null;
  is_verified: boolean;
  is_active: boolean;
}

export type EmploymentType =
  | "FULL_TIME"
  | "PART_TIME"
  | "CONTRACT"
  | "INTERNSHIP"
  | "TEMPORARY"
  | "VOLUNTEER";

export type WorkMode = "ON_SITE" | "REMOTE" | "HYBRID";

export type ExperienceLevel = "ENTRY" | "JUNIOR" | "MID" | "SENIOR" | "LEAD" | "EXECUTIVE";

export type SourceType =
  | "OFFICIAL_CAREER_PAGE"
  | "OFFICIAL_NEWSROOM"
  | "RSS"
  | "LEVER"
  | "ASHBY"
  | "OTHER";

export type ContentStatus = "DRAFT" | "REVIEW" | "PUBLISHED" | "EXPIRED" | "ARCHIVED";

export interface JobAdmin {
  id: string;
  slug: string;
  title: string;
  company: Company;
  location: string | null;
  city: string | null;
  country: string | null;
  employment_type: EmploymentType;
  work_mode: WorkMode;
  experience_level: ExperienceLevel | null;
  industry: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  salary_period: string | null;
  short_summary: string | null;
  description: string | null;
  responsibilities: string[] | null;
  requirements: string[] | null;
  preferred_skills: string[] | null;
  benefits: string[] | null;
  thumbnail_url: string | null;
  post_image_url: string | null;
  image_alt_text: string | null;
  application_url: string | null;
  application_email: string | null;
  application_instructions: string | null;
  source_type: SourceType;
  source_url: string | null;
  source_published_at: string | null;
  published_at: string | null;
  application_deadline: string | null;
  expires_at: string | null;
  is_verified: boolean;
  is_featured: boolean;
  is_urgent: boolean;
  is_active: boolean;
  is_demo: boolean;
  status: ContentStatus;
  created_by_admin_id: string | null;
  scheduled_publish_at: string | null;
  reviewed_by_admin_id: string | null;
  published_by_admin_id: string | null;
}

export interface JobCompanySummary {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
}

export type IntelligenceCategory =
  | "LEADERSHIP" | "TECHNOLOGY" | "AUTOMATION" | "INVESTMENTS" | "HIRING" | "PROJECTS"
  | "ACQUISITION" | "PLANT_EXPANSION" | "MANUFACTURING" | "ENERGY" | "FINANCE" | "AI"
  | "GRADUATE_RECRUITMENT" | "OPERATIONS" | "OTHER";

export interface IntelligencePostAdmin {
  id: string;
  slug: string;
  headline: string;
  category: IntelligenceCategory;
  company: JobCompanySummary | null;
  company_id: string | null;
  thumbnail_url: string | null;
  post_image_url: string | null;
  image_alt_text: string | null;
  summary: string | null;
  full_content: string | null;
  why_it_matters: string | null;
  relevant_roles: string[] | null;
  relevant_skills: string[] | null;
  source_type: SourceType;
  source_url: string | null;
  source_published_at: string | null;
  published_at: string | null;
  is_verified: boolean;
  is_featured: boolean;
  is_active: boolean;
  is_demo: boolean;
  status: ContentStatus;
  created_by_admin_id: string | null;
  scheduled_publish_at: string | null;
  reviewed_by_admin_id: string | null;
  published_by_admin_id: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export type DegreeLevel = "UNDERGRADUATE" | "MASTERS" | "PHD" | "OTHER";
export type FundingType = "FULLY_FUNDED" | "PARTIAL";

export interface ScholarshipAdmin {
  id: string;
  slug: string;
  name: string;
  organization: string | null;
  country: string | null;
  degree_levels: DegreeLevel[] | null;
  fields_of_study: string[] | null;
  funding_type: FundingType;
  tuition_coverage: string | null;
  monthly_stipend: string | null;
  travel_support: string | null;
  insurance_support: string | null;
  accommodation_support: string | null;
  summary: string | null;
  description: string | null;
  eligible_nationalities: string[] | null;
  academic_requirements: string[] | null;
  experience_requirements: string[] | null;
  language_requirements: string[] | null;
  age_requirement: string | null;
  required_documents: string[] | null;
  thumbnail_url: string | null;
  post_image_url: string | null;
  image_alt_text: string | null;
  official_url: string | null;
  source_url: string | null;
  source_type: SourceType;
  source_published_at: string | null;
  application_deadline: string | null;
  published_at: string | null;
  is_verified: boolean;
  is_featured: boolean;
  is_active: boolean;
  is_demo: boolean;
  status: ContentStatus;
  created_by_admin_id: string | null;
  scheduled_publish_at: string | null;
  reviewed_by_admin_id: string | null;
  published_by_admin_id: string | null;
}
