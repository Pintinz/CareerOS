import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.interview.answer_check import answer_structure_check, word_count
from app.interview.checklist import (
    COMPANY_PREP_CHECKLIST_KEYS,
    DEFAULT_CHECKLIST_ITEMS,
    QUESTIONS_TO_ASK_CATALOG,
)
from app.interview.generator import generate_questions
from app.interview.job_role_topic_map import topics_for
from app.interview.readiness import compute_readiness
from app.interview.role_mix import GENERAL_DEFAULT_MIX, category_counts_for_mix, default_mix_for
from app.interview.star_check import star_completeness_check
from app.models.company import Company
from app.models.interview import (
    InterviewAnswer,
    InterviewPreparationProgress,
    InterviewQuestion,
    InterviewQuestionCategory,
    InterviewRecording,
    InterviewSession,
    InterviewSessionQuestion,
    InterviewSessionStatus,
    InterviewTopic,
    StarStory,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.interview_progress_repository import InterviewProgressRepository
from app.repositories.interview_recording_repository import InterviewRecordingRepository
from app.repositories.interview_repository import (
    InterviewCategoryRepository,
    InterviewQuestionRepository,
    InterviewTopicRepository,
)
from app.repositories.interview_session_repository import InterviewSessionRepository
from app.repositories.intelligence_repository import IntelligenceRepository
from app.repositories.job_repository import JobRepository
from app.repositories.star_story_repository import StarStoryRepository
from app.schemas.interview import (
    AnswerStructureCheckOut,
    AnswerUpdate,
    CategoryCompletionOut,
    ChecklistItemOut,
    CompanyPrepOut,
    InterviewAnalyticsOut,
    InterviewCategoryCreate,
    InterviewQuestionAdminOut,
    InterviewQuestionCreate,
    InterviewQuestionUpdate,
    InterviewSessionCreate,
    InterviewSessionDetailOut,
    InterviewSessionOut,
    InterviewTopicCreate,
    MockMixPreviewOut,
    OpenJobOut,
    PreparationProgressOut,
    QuestionToAskOut,
    ReadinessOut,
    RecentDevelopmentOut,
    RecordingCreate,
    RecordingOut,
    SessionAnswerStateOut,
    SessionCompletionOut,
    SessionQuestionOut,
    StarCompletenessOut,
    StarStoryCreate,
    StarStoryOut,
    StarStoryUpdate,
)


class InterviewService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sessions = InterviewSessionRepository(db)
        self.questions = InterviewQuestionRepository(db)
        self.categories = InterviewCategoryRepository(db)
        self.topics = InterviewTopicRepository(db)
        self.stars = StarStoryRepository(db)
        self.progress = InterviewProgressRepository(db)
        self.recordings = InterviewRecordingRepository(db)

    # -- admin: question bank CRUD -------------------------------------------------------------

    async def admin_list_categories(self) -> list[InterviewQuestionCategory]:
        return await self.categories.list_all()

    async def admin_create_category(self, payload: InterviewCategoryCreate) -> InterviewQuestionCategory:
        category = await self.categories.create(InterviewQuestionCategory(**payload.model_dump()))
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def admin_list_topics(self, category_id: str | None):
        return await self.topics.list_all(category_id=category_id)

    async def admin_create_topic(self, payload: InterviewTopicCreate):
        topic = await self.topics.create(InterviewTopic(**payload.model_dump()))
        await self.db.commit()
        await self.db.refresh(topic)
        return topic

    async def admin_list_questions(self, *, page: int, page_size: int, category_id: str | None, search: str | None):
        items, total = await self.questions.list_admin(page=page, page_size=page_size, category_id=category_id, search=search)
        return items, total

    async def admin_get_question(self, question_id: str) -> InterviewQuestionAdminOut:
        question = await self.questions.get_by_id(question_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        return InterviewQuestionAdminOut.model_validate(question)

    async def admin_create_question(self, payload: InterviewQuestionCreate, admin_id: str) -> InterviewQuestionAdminOut:
        data = payload.model_dump()
        guidance = data.pop("answer_guidance", None)
        question = InterviewQuestion(**data, answer_guidance=guidance, created_by_admin_id=admin_id)
        await self.questions.create(question)
        await self.db.commit()
        return await self.admin_get_question(question.id)

    async def admin_update_question(self, question_id: str, payload: InterviewQuestionUpdate) -> InterviewQuestionAdminOut:
        question = await self.questions.get_by_id(question_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(question, field, value)
        self.db.add(question)
        await self.db.commit()
        return await self.admin_get_question(question_id)

    async def admin_delete_question(self, question_id: str) -> None:
        question = await self.questions.get_by_id(question_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        await self.questions.delete(question)
        await self.db.commit()

    async def get_mock_mix_preview(
        self, user_id: str, *, question_count: int, application_id: str | None, job_id: str | None
    ) -> MockMixPreviewOut:
        fake_payload = InterviewSessionCreate(
            question_count=question_count, application_id=application_id, job_id=job_id
        )
        field, industry, job_role, _, _ = await self._resolve_context(user_id, fake_payload)
        mix = default_mix_for(field=field, industry=industry, job_role=job_role)
        counts = category_counts_for_mix(mix, question_count)
        names = {}
        for slug in counts:
            category = await self.categories.get_by_slug(slug)
            names[slug] = category.name if category else slug
        source = "general_default" if mix is GENERAL_DEFAULT_MIX else "role_default"
        return MockMixPreviewOut(category_counts=counts, category_names=names, source=source)

    # -- session creation -----------------------------------------------------------------------

    async def create_session(self, user_id: str, payload: InterviewSessionCreate) -> InterviewSessionDetailOut:
        field, industry, job_role, company_id, job_id = await self._resolve_context(user_id, payload)

        category_counts_slugs = payload.category_counts
        if payload.auto_mix and not category_counts_slugs:
            mix = default_mix_for(field=field, industry=industry, job_role=job_role)
            category_counts_slugs = category_counts_for_mix(mix, payload.question_count)

        category_ids = await self._resolve_category_ids(payload.categories, category_counts_slugs)
        category_counts_by_id = await self._resolve_category_counts(category_counts_slugs)

        candidate_questions = await generate_questions(
            self.questions,
            category_ids=category_ids,
            difficulty=payload.difficulty,
            question_count=payload.question_count,
            field=field,
            industry=industry,
            job_role=job_role,
            company_id=company_id,
            experience_level=payload.experience_level.value if payload.experience_level else None,
            category_counts=category_counts_by_id,
        )
        if not candidate_questions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No active interview questions match the selected categories/difficulty yet.",
            )

        now = datetime.now(timezone.utc)
        session = InterviewSession(
            user_id=user_id,
            mode=payload.mode,
            status=InterviewSessionStatus.IN_PROGRESS,
            application_id=payload.application_id,
            job_id=job_id or payload.job_id,
            company_id=company_id or payload.company_id,
            config=payload.model_dump(mode="json"),
            categories_requested=payload.categories,
            time_per_question_seconds=payload.time_per_question_seconds,
            started_at=now,
            question_count=len(candidate_questions),
        )
        await self.sessions.create(session)

        for index, question in enumerate(candidate_questions):
            category = await self.categories.get_by_id(question.category_id)
            topic = await self.topics.get_by_id(question.topic_id) if question.topic_id else None
            await self.sessions.add_question(
                InterviewSessionQuestion(
                    session_id=session.id,
                    question_id=question.id,
                    order_index=index,
                    question_text=question.question_text,
                    category_slug=category.slug if category else "unknown",
                    category_name=category.name if category else "Unknown",
                    topic_name=topic.name if topic else None,
                    difficulty=question.difficulty,
                    answer_guidance=question.answer_guidance,
                    evaluation_points=question.evaluation_points,
                    follow_up_prompt=question.follow_up_prompt,
                    star_tags=question.star_tags,
                    time_limit_seconds=payload.time_per_question_seconds,
                )
            )

        await self.db.commit()
        await self.db.refresh(session)
        return await self.get_session_detail(user_id, session.id)

    async def _resolve_category_ids(self, category_slugs: list[str], category_counts: dict[str, int] | None) -> list[str]:
        slugs = category_slugs or (list(category_counts.keys()) if category_counts else [])
        if not slugs:
            return [c.id for c in await self.categories.list_all()]
        ids = []
        for slug in slugs:
            category = await self.categories.get_by_slug(slug)
            if category is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown category '{slug}'")
            ids.append(category.id)
        return ids

    async def _resolve_category_counts(self, category_counts: dict[str, int] | None) -> dict[str, int] | None:
        if not category_counts:
            return None
        resolved = {}
        for slug, count in category_counts.items():
            category = await self.categories.get_by_slug(slug)
            if category is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown category '{slug}'")
            resolved[category.id] = count
        return resolved

    async def _resolve_context(
        self, user_id: str, payload: InterviewSessionCreate
    ) -> tuple[str | None, str | None, str | None, str | None, str | None]:
        """Returns (field, industry, job_role, company_id, job_id)."""
        if payload.job_id:
            job = await JobRepository(self.db).get_by_id(payload.job_id)
            if job is None:
                return None, None, None, payload.company_id, None
            return None, job.industry, job.title, job.company_id, job.id

        if payload.application_id:
            application = await ApplicationRepository(self.db).get_owned(payload.application_id, user_id)
            if application is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
            job = await JobRepository(self.db).get_by_id(application.job_id) if application.job_id else None
            company_id = job.company_id if job else None
            if company_id is None:
                company = await CompanyRepository(self.db).get_by_name(application.company_name)
                company_id = company.id if company else None
            industry = job.industry if job else None
            job_role = (job.title if job else None) or application.role_title
            return None, industry, job_role, company_id, (job.id if job else None)

        return None, None, None, payload.company_id, None

    # -- fetching ---------------------------------------------------------------------------------

    async def _get_owned_or_404(self, user_id: str, session_id: str) -> InterviewSession:
        session = await self.sessions.get_owned(session_id, user_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found")
        return session

    async def get_session_detail(self, user_id: str, session_id: str) -> InterviewSessionDetailOut:
        session = await self._get_owned_or_404(user_id, session_id)
        session_questions = await self.sessions.get_session_questions(session_id)
        answers = {a.session_question_id: a for a in await self.sessions.get_answers_for_session(session_id)}
        stories = await self.stars.list_for_user(user_id)

        questions_out = []
        for sq in session_questions:
            answer = answers.get(sq.id)
            answer_state = None
            if answer:
                structure_check = None
                if answer.answer_text:
                    check = answer_structure_check(answer.answer_text)
                    structure_check = AnswerStructureCheckOut(**check)
                answer_state = SessionAnswerStateOut(
                    answer_text=answer.answer_text,
                    notes=answer.notes,
                    audio_path=answer.audio_path,
                    audio_duration_seconds=answer.audio_duration_seconds,
                    self_rating=answer.self_rating,
                    used_star=answer.used_star,
                    gave_measurable_result=answer.gave_measurable_result,
                    answered_exact_question=answer.answered_exact_question,
                    is_skipped=answer.is_skipped,
                    is_marked_practiced=answer.is_marked_practiced,
                    is_saved=answer.is_saved,
                    structure_check=structure_check,
                )
            suggested_ids = [
                story.id for story in stories if sq.star_tags and story.category.value.lower() in sq.star_tags
            ]
            questions_out.append(
                SessionQuestionOut(
                    id=sq.id,
                    order_index=sq.order_index,
                    question_text=sq.question_text,
                    category_name=sq.category_name,
                    topic_name=sq.topic_name,
                    difficulty=sq.difficulty,
                    answer_guidance=sq.answer_guidance,
                    evaluation_points=sq.evaluation_points,
                    follow_up_prompt=sq.follow_up_prompt,
                    suggested_star_story_ids=suggested_ids,
                    time_limit_seconds=sq.time_limit_seconds,
                    answer_state=answer_state,
                )
            )

        base = InterviewSessionOut.model_validate(session).model_dump()
        base["questions"] = questions_out
        return InterviewSessionDetailOut.model_validate(base)

    async def list_for_user(self, user_id: str, *, page: int, page_size: int, status_filter: str | None):
        items, total = await self.sessions.list_for_user(user_id, page=page, page_size=page_size, status=status_filter)
        return [InterviewSessionOut.model_validate(s) for s in items], total

    # -- answering ----------------------------------------------------------------------------------

    async def update_answer(
        self, user_id: str, session_id: str, session_question_id: str, payload: AnswerUpdate
    ) -> SessionQuestionOut:
        session = await self._get_owned_or_404(user_id, session_id)
        if session.status != InterviewSessionStatus.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session is no longer in progress.")

        sq = await self.sessions.get_session_question(session_id, session_question_id)
        if sq is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in this session")

        answer = await self.sessions.get_answer(session_question_id)
        if answer is None:
            answer = InterviewAnswer(session_id=session_id, session_question_id=session_question_id)

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(answer, field, value)
        if payload.answer_text is not None:
            answer.word_count = word_count(payload.answer_text)

        await self.sessions.upsert_answer(answer)
        await self.db.commit()

        detail = await self.get_session_detail(user_id, session_id)
        return next(q for q in detail.questions if q.id == session_question_id)

    # -- completion -----------------------------------------------------------------------------

    async def complete_session(self, user_id: str, session_id: str) -> SessionCompletionOut:
        session = await self._get_owned_or_404(user_id, session_id)
        if session.status == InterviewSessionStatus.IN_PROGRESS:
            session.status = InterviewSessionStatus.COMPLETED
            session.completed_at = datetime.now(timezone.utc)
            self.db.add(session)
            await self.db.commit()
        elif session.status != InterviewSessionStatus.COMPLETED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session cannot be completed.")

        session_questions = await self.sessions.get_session_questions(session_id)
        answers = {a.session_question_id: a for a in await self.sessions.get_answers_for_session(session_id)}

        completed = 0
        skipped = 0
        ratings: list[int] = []
        lengths: list[int] = []
        star_used_count = 0
        answered_count = 0
        category_totals: dict[str, dict[str, int]] = {}

        for sq in session_questions:
            category_totals.setdefault(sq.category_name, {"completed": 0, "total": 0})
            category_totals[sq.category_name]["total"] += 1
            answer = answers.get(sq.id)
            if answer is None:
                continue
            if answer.is_skipped:
                skipped += 1
                continue
            if answer.answer_text or answer.is_marked_practiced or answer.audio_path:
                completed += 1
                category_totals[sq.category_name]["completed"] += 1
                if answer.self_rating is not None:
                    ratings.append(answer.self_rating)
                if answer.word_count is not None:
                    lengths.append(answer.word_count)
                if answer.used_star is not None:
                    answered_count += 1
                    if answer.used_star:
                        star_used_count += 1

        areas_practiced = [name for name, stats in category_totals.items() if stats["completed"] > 0]
        areas_uncovered = [name for name, stats in category_totals.items() if stats["completed"] == 0]

        return SessionCompletionOut(
            session_id=session.id,
            questions_completed=completed,
            questions_skipped=skipped,
            average_self_rating=round(sum(ratings) / len(ratings), 1) if ratings else None,
            average_answer_length=round(sum(lengths) / len(lengths), 1) if lengths else None,
            star_usage_rate=round((star_used_count / answered_count) * 100, 1) if answered_count else None,
            category_breakdown={
                name: CategoryCompletionOut(completed=stats["completed"], total=stats["total"])
                for name, stats in category_totals.items()
            },
            areas_practiced=areas_practiced,
            areas_still_uncovered=areas_uncovered,
        )

    # -- analytics / readiness -------------------------------------------------------------------

    async def get_analytics(self, user_id: str) -> InterviewAnalyticsOut:
        completed_sessions = await self.sessions.list_completed_for_user(user_id)
        all_sessions, _ = await self.sessions.list_for_user(user_id, page=1, page_size=1000)

        questions_practiced_ids: set[str] = set()
        ratings: list[int] = []
        category_totals: dict[str, dict[str, int]] = {}

        for session in all_sessions:
            session_questions = await self.sessions.get_session_questions(session.id)
            answers = {a.session_question_id: a for a in await self.sessions.get_answers_for_session(session.id)}
            for sq in session_questions:
                category_totals.setdefault(sq.category_name, {"completed": 0, "total": 0})
                category_totals[sq.category_name]["total"] += 1
                answer = answers.get(sq.id)
                if answer is None or answer.is_skipped:
                    continue
                if answer.answer_text or answer.is_marked_practiced or answer.audio_path:
                    questions_practiced_ids.add(sq.id)
                    category_totals[sq.category_name]["completed"] += 1
                    if answer.self_rating is not None:
                        ratings.append(answer.self_rating)

        stories = await self.stars.list_for_user(user_id)
        ready_stories = [s for s in stories if star_completeness_check(
            situation=s.situation, task=s.task, action=s.action, result=s.result
        )["is_complete"]]

        progress_rows = await self.progress.list_for_user(user_id)
        company_prep_completed = sum(
            1 for p in progress_rows if p.application_id and all(p.checklist.get(k) for k in COMPANY_PREP_CHECKLIST_KEYS)
        )
        reviewed_topics: set[str] = set()
        for p in progress_rows:
            reviewed_topics.update(p.reviewed_topics or [])

        return InterviewAnalyticsOut(
            sessions_completed=len(completed_sessions),
            questions_practiced=len(questions_practiced_ids),
            average_self_rating=round(sum(ratings) / len(ratings), 1) if ratings else None,
            star_stories_created=len(stories),
            star_stories_ready=len(ready_stories),
            company_prep_completed=company_prep_completed,
            technical_topics_covered=len(reviewed_topics),
            by_category={
                name: CategoryCompletionOut(completed=stats["completed"], total=stats["total"])
                for name, stats in category_totals.items()
            },
        )

    async def get_readiness(self, user_id: str, application_id: str | None = None) -> ReadinessOut:
        all_sessions, _ = await self.sessions.list_for_user(user_id, page=1, page_size=1000)

        questions_practiced_ids: set[str] = set()
        technical_practiced_ids: set[str] = set()
        job_specific_practiced_ids: set[str] = set()
        last_activity: datetime | None = None

        for session in all_sessions:
            if application_id and session.application_id != application_id:
                continue
            session_questions = await self.sessions.get_session_questions(session.id)
            answers = {a.session_question_id: a for a in await self.sessions.get_answers_for_session(session.id)}
            for sq in session_questions:
                answer = answers.get(sq.id)
                if answer is None or answer.is_skipped:
                    continue
                if answer.answer_text or answer.is_marked_practiced or answer.audio_path:
                    questions_practiced_ids.add(sq.id)
                    if sq.category_slug == "technical":
                        technical_practiced_ids.add(sq.id)
                    if sq.category_slug in ("job_specific", "technical"):
                        job_specific_practiced_ids.add(sq.id)
                    if last_activity is None or answer.updated_at > last_activity:
                        last_activity = answer.updated_at

        stories = await self.stars.list_for_user(user_id)
        ready_count = sum(
            1 for s in stories
            if star_completeness_check(situation=s.situation, task=s.task, action=s.action, result=s.result)["is_complete"]
        )

        company_done = None
        company_total = 0
        job_specific_count = None
        if application_id:
            progress = await self.progress.get_or_create(user_id, application_id)
            company_total = len(COMPANY_PREP_CHECKLIST_KEYS)
            company_done = sum(1 for key in COMPANY_PREP_CHECKLIST_KEYS if progress.checklist.get(key))
            job_specific_count = len(job_specific_practiced_ids)

        days_since = None
        if last_activity is not None:
            days_since = (datetime.now(timezone.utc) - _as_aware_utc(last_activity)).days

        result = compute_readiness(
            questions_practiced=len(questions_practiced_ids),
            star_ready_count=ready_count,
            technical_questions_practiced=len(technical_practiced_ids),
            days_since_last_practice=days_since,
            company_checklist_done=company_done,
            company_checklist_total=company_total,
            job_specific_questions_practiced=job_specific_count,
        )
        return ReadinessOut.model_validate(result)

    # -- STAR stories -------------------------------------------------------------------------------

    def _star_out(self, story: StarStory) -> StarStoryOut:
        check = star_completeness_check(situation=story.situation, task=story.task, action=story.action, result=story.result)
        base = {
            "id": story.id, "title": story.title, "category": story.category, "situation": story.situation,
            "task": story.task, "action": story.action, "result": story.result, "lessons": story.lessons,
            "skills_demonstrated": story.skills_demonstrated, "metrics": story.metrics,
            "company_context": story.company_context, "relevant_roles": story.relevant_roles,
            "relevant_questions": story.relevant_questions, "version": story.version,
            "created_at": story.created_at, "updated_at": story.updated_at,
            "completeness": StarCompletenessOut(**check),
        }
        return StarStoryOut.model_validate(base)

    async def create_star_story(self, user_id: str, payload: StarStoryCreate) -> StarStoryOut:
        story = StarStory(user_id=user_id, **payload.model_dump())
        await self.stars.create(story)
        await self.db.commit()
        await self.db.refresh(story)
        return self._star_out(story)

    async def list_star_stories(self, user_id: str, category: str | None = None) -> list[StarStoryOut]:
        stories = await self.stars.list_for_user(user_id, category=category)
        return [self._star_out(s) for s in stories]

    async def get_star_story(self, user_id: str, story_id: str) -> StarStoryOut:
        story = await self.stars.get_owned(story_id, user_id)
        if story is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="STAR story not found")
        return self._star_out(story)

    async def update_star_story(self, user_id: str, story_id: str, payload: StarStoryUpdate) -> StarStoryOut:
        story = await self.stars.get_owned(story_id, user_id)
        if story is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="STAR story not found")
        if payload.expected_version is not None and payload.expected_version != story.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This story was updated elsewhere since you last loaded it.",
            )
        for field, value in payload.model_dump(exclude_unset=True, exclude={"expected_version"}).items():
            setattr(story, field, value)
        story.version += 1
        self.db.add(story)
        await self.db.commit()
        await self.db.refresh(story)
        return self._star_out(story)

    async def delete_star_story(self, user_id: str, story_id: str) -> None:
        story = await self.stars.get_owned(story_id, user_id)
        if story is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="STAR story not found")
        await self.stars.delete(story)
        await self.db.commit()

    # -- company / job preparation ---------------------------------------------------------------

    async def get_company_prep(self, user_id: str, application_id: str) -> CompanyPrepOut:
        application = await ApplicationRepository(self.db).get_owned(application_id, user_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

        job = await JobRepository(self.db).get_by_id(application.job_id) if application.job_id else None
        company: Company | None = None
        if job is not None:
            company = await CompanyRepository(self.db).get_by_id(job.company_id)
        if company is None:
            company = await CompanyRepository(self.db).get_by_name(application.company_name)

        recent_posts = []
        if company is not None:
            posts, _ = await IntelligenceRepository(self.db).list_public(page=1, page_size=5, company_id=company.id)
            recent_posts = [
                RecentDevelopmentOut(id=p.id, headline=p.headline, summary=p.summary, published_at=p.published_at)
                for p in posts
            ]

        open_jobs_out = []
        if company is not None:
            jobs, _ = await JobRepository(self.db).list_public(page=1, page_size=5, company_id=company.id)
            open_jobs_out = [OpenJobOut(id=j.id, title=j.title, location=j.location) for j in jobs]

        likely_topics = topics_for(
            field=None, industry=(job.industry if job else company.industry if company else None),
            job_role=(job.title if job else application.role_title),
        )

        role_relevance = None
        if job is not None:
            role_relevance = (
                f"This role ({job.title}) is in {job.industry or 'an unspecified industry'}. "
                f"Focus your preparation on the responsibilities and requirements listed on the job posting."
            )
        elif application.role_title:
            role_relevance = f"Preparing for {application.role_title} at {application.company_name}."

        return CompanyPrepOut(
            company_id=company.id if company else None,
            company_name=company.name if company else application.company_name,
            industry=(company.industry if company else job.industry if job else None),
            about=company.description if company else None,
            recent_developments=recent_posts,
            role_relevance=role_relevance,
            likely_topics=likely_topics,
            open_jobs=open_jobs_out,
        )

    # -- checklist / questions to ask / topic review -----------------------------------------------

    async def get_preparation_progress(self, user_id: str, application_id: str | None) -> PreparationProgressOut:
        progress = await self.progress.get_or_create(user_id, application_id)
        return self._progress_out(progress)

    def _progress_out(self, progress: InterviewPreparationProgress) -> PreparationProgressOut:
        checklist_out = [
            ChecklistItemOut(key=key, label=label, is_done=bool(progress.checklist.get(key)))
            for key, label in DEFAULT_CHECKLIST_ITEMS
        ]
        saved_or_planned = {q["id"]: q for q in progress.questions_to_ask if not q.get("is_custom")}
        catalog_out = [
            QuestionToAskOut(
                id=qid, text=text, category=category,
                status=saved_or_planned.get(qid, {}).get("status"),
            )
            for qid, text, category in QUESTIONS_TO_ASK_CATALOG
        ]
        custom_out = [
            QuestionToAskOut(id=q["id"], text=q["text"], category=q.get("category", "Role"), status=q.get("status"), is_custom=True)
            for q in progress.questions_to_ask if q.get("is_custom")
        ]
        return PreparationProgressOut(
            application_id=progress.application_id,
            checklist=checklist_out,
            questions_to_ask=catalog_out + custom_out,
            reviewed_topics=progress.reviewed_topics,
            version=progress.version,
        )

    def _check_version(self, progress: InterviewPreparationProgress, expected_version: int | None) -> None:
        if expected_version is not None and expected_version != progress.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This preparation progress was updated elsewhere since you last loaded it.",
            )

    async def update_checklist_item(
        self, user_id: str, application_id: str | None, key: str, is_done: bool, expected_version: int | None = None
    ) -> PreparationProgressOut:
        progress = await self.progress.get_or_create(user_id, application_id)
        self._check_version(progress, expected_version)
        valid_keys = {k for k, _ in DEFAULT_CHECKLIST_ITEMS}
        if key not in valid_keys:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown checklist item '{key}'")
        checklist = dict(progress.checklist)
        checklist[key] = is_done
        progress.checklist = checklist
        progress.version += 1
        self.db.add(progress)
        await self.db.commit()
        return self._progress_out(progress)

    async def update_question_to_ask(self, user_id: str, application_id: str | None, payload) -> PreparationProgressOut:
        progress = await self.progress.get_or_create(user_id, application_id)
        self._check_version(progress, payload.expected_version)
        entries = [q for q in progress.questions_to_ask if q["id"] != payload.id] if payload.id else list(progress.questions_to_ask)
        entry_id = payload.id or f"custom-{uuid.uuid4().hex[:8]}"
        if payload.status is not None or payload.is_custom or payload.text:
            entries.append({
                "id": entry_id,
                "text": payload.text or "",
                "category": payload.category or "Role",
                "status": payload.status,
                "is_custom": payload.is_custom,
            })
        progress.questions_to_ask = entries
        progress.version += 1
        self.db.add(progress)
        await self.db.commit()
        return self._progress_out(progress)

    async def update_topic_review(
        self, user_id: str, application_id: str | None, topic_slug: str, is_reviewed: bool, expected_version: int | None = None
    ) -> PreparationProgressOut:
        progress = await self.progress.get_or_create(user_id, application_id)
        self._check_version(progress, expected_version)
        reviewed = set(progress.reviewed_topics)
        if is_reviewed:
            reviewed.add(topic_slug)
        else:
            reviewed.discard(topic_slug)
        progress.reviewed_topics = list(reviewed)
        progress.version += 1
        self.db.add(progress)
        await self.db.commit()
        return self._progress_out(progress)

    # -- recordings (metadata only — the audio binary stays on-device, spec §4/§37) -----------------

    async def create_recording(self, user_id: str, payload: RecordingCreate) -> RecordingOut:
        session = await self._get_owned_or_404(user_id, payload.session_id)
        session_question = await self.sessions.get_session_question(session.id, payload.session_question_id)
        if session_question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in this session")

        recording = InterviewRecording(
            user_id=user_id,
            session_id=payload.session_id,
            session_question_id=payload.session_question_id,
            local_path=payload.local_path,
            duration_seconds=payload.duration_seconds,
            title=payload.title,
        )
        self.recordings.add(recording)
        await self.db.commit()
        await self.db.refresh(recording)
        return RecordingOut.model_validate(recording)

    async def list_recordings(self, user_id: str) -> list[RecordingOut]:
        recordings = await self.recordings.list_for_user(user_id)
        return [RecordingOut.model_validate(r) for r in recordings]

    async def update_recording(self, user_id: str, recording_id: str, title: str) -> RecordingOut:
        recording = await self.recordings.get_owned(recording_id, user_id)
        if recording is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")
        recording.title = title
        self.db.add(recording)
        await self.db.commit()
        await self.db.refresh(recording)
        return RecordingOut.model_validate(recording)

    async def delete_recording(self, user_id: str, recording_id: str) -> None:
        recording = await self.recordings.get_owned(recording_id, user_id)
        if recording is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")
        await self.recordings.delete(recording)
        await self.db.commit()


def _as_aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
