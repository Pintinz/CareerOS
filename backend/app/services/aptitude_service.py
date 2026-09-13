from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.aptitude.generator import generate_questions
from app.aptitude.scoring import (
    MAX_WEAK_TOPICS_RETURNED,
    MIN_ATTEMPTS_FOR_TOPIC_RECOMMENDATION,
    WEAK_TOPIC_ACCURACY_THRESHOLD,
    performance_label,
)
from app.models.application import Application
from app.models.job import Job
from app.models.question import Question, QuestionCategory, QuestionOption, QuestionTopic, QuestionType
from app.models.test_session import TestAnswer, TestSession, TestSessionQuestion, TestStatus
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.question_repository import (
    QuestionCategoryRepository,
    QuestionRepository,
    QuestionTopicRepository,
)
from app.repositories.test_session_repository import TestSessionRepository
from app.schemas.aptitude import (
    AnswerUpdate,
    AptitudeAnalyticsOut,
    CategoryStat,
    OptionOut,
    QuestionAdminOut,
    QuestionCategoryCreate,
    QuestionCreate,
    QuestionTopicCreate,
    QuestionUpdate,
    RecommendationsOut,
    ReviewOptionOut,
    ReviewOut,
    ReviewQuestionOut,
    SessionAnswerStateOut,
    SessionQuestionOut,
    TestResultOut,
    TestSessionCreate,
    TestSessionDetailOut,
    TestSessionOut,
    TopicStat,
    WeakTopicOut,
)


class AptitudeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sessions = TestSessionRepository(db)
        self.questions = QuestionRepository(db)
        self.categories = QuestionCategoryRepository(db)
        self.topics = QuestionTopicRepository(db)

    # -- admin: question bank CRUD (never exposed to normal users, spec §14/§35) --------------

    async def admin_list_categories(self) -> list[QuestionCategory]:
        return await self.categories.list_all()

    async def admin_create_category(self, payload: QuestionCategoryCreate) -> QuestionCategory:
        category = await self.categories.create(QuestionCategory(**payload.model_dump()))
        await self.db.commit()
        return category

    async def admin_list_topics(self, category_id: str | None) -> list:
        return await self.topics.list_all(category_id=category_id)

    async def admin_create_topic(self, payload: QuestionTopicCreate) -> QuestionTopic:
        topic = await self.topics.create(QuestionTopic(**payload.model_dump()))
        await self.db.commit()
        return topic

    async def admin_list_questions(
        self, *, page: int, page_size: int, category_id: str | None, search: str | None
    ) -> tuple[list[QuestionAdminOut], int]:
        items, total = await self.questions.list_admin(
            page=page, page_size=page_size, category_id=category_id, search=search
        )
        out = []
        for question in items:
            options = await self.questions.get_options(question.id)
            out.append(self._question_to_admin_out(question, options))
        return out, total

    async def admin_get_question(self, question_id: str) -> QuestionAdminOut:
        question = await self.questions.get_by_id(question_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        options = await self.questions.get_options(question_id)
        return self._question_to_admin_out(question, options)

    async def admin_create_question(self, payload: QuestionCreate, admin_id: str) -> QuestionAdminOut:
        data = payload.model_dump(exclude={"options"})
        question = Question(**data, created_by_admin_id=admin_id)
        await self.questions.create(question)
        options = [QuestionOption(**opt.model_dump()) for opt in payload.options]
        await self.questions.replace_options(question.id, options)
        await self.db.commit()
        return await self.admin_get_question(question.id)

    async def admin_update_question(self, question_id: str, payload: QuestionUpdate) -> QuestionAdminOut:
        question = await self.questions.get_by_id(question_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        for field, value in payload.model_dump(exclude={"options"}, exclude_unset=True).items():
            setattr(question, field, value)
        self.db.add(question)

        if payload.options is not None:
            options = [QuestionOption(**opt.model_dump()) for opt in payload.options]
            await self.questions.replace_options(question_id, options)

        await self.db.commit()
        return await self.admin_get_question(question_id)

    async def admin_delete_question(self, question_id: str) -> None:
        question = await self.questions.get_by_id(question_id)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        await self.questions.delete(question)
        await self.db.commit()

    @staticmethod
    def _question_to_admin_out(question: Question, options: list[QuestionOption]) -> QuestionAdminOut:
        fields = {name: getattr(question, name) for name in QuestionAdminOut.model_fields if name != "options"}
        fields["options"] = options
        return QuestionAdminOut.model_validate(fields)

    # -- session creation ---------------------------------------------------

    async def create_session(self, user_id: str, payload: TestSessionCreate) -> TestSessionDetailOut:
        category_ids = await self._resolve_category_ids(payload.sections)

        field, industry, job_role = await self._resolve_job_context(user_id, payload)

        candidate_questions = await generate_questions(
            self.questions,
            category_ids=category_ids,
            difficulty=payload.difficulty,
            question_count=payload.question_count,
            field=field,
            industry=industry,
            job_role=job_role,
            topic_slugs_override=payload.topic_slugs,
        )
        if not candidate_questions:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No active questions match the selected sections/difficulty yet.",
            )

        now = datetime.now(timezone.utc)
        time_limit_seconds = None
        expires_at = None
        if payload.timing == "OVERALL" and payload.time_limit_minutes:
            time_limit_seconds = payload.time_limit_minutes * 60
            expires_at = now + timedelta(seconds=time_limit_seconds)

        session = TestSession(
            user_id=user_id,
            mode=payload.mode,
            status=TestStatus.IN_PROGRESS,
            application_id=payload.application_id,
            job_id=payload.job_id,
            config=payload.model_dump(mode="json"),
            started_at=now,
            expires_at=expires_at,
            time_limit_seconds=time_limit_seconds,
            question_count=len(candidate_questions),
            total_marks=sum(q.marks for q in candidate_questions),
        )
        await self.sessions.create(session)

        for index, question in enumerate(candidate_questions):
            options = await self.questions.get_options(question.id)
            options_snapshot = [
                {
                    "id": opt.id,
                    "option_text": opt.option_text,
                    "option_image_url": opt.option_image_url,
                    "option_image_alt_text": opt.option_image_alt_text,
                    "display_order": opt.display_order,
                }
                for opt in options
            ]
            correct_option_ids = [opt.id for opt in options if opt.is_correct]
            category = await self.categories.get_by_id(question.category_id)
            topic = await self.topics.get_by_id(question.topic_id) if question.topic_id else None

            await self.sessions.add_question(
                TestSessionQuestion(
                    session_id=session.id,
                    question_id=question.id,
                    order_index=index,
                    question_text=question.question_text,
                    question_type=question.question_type,
                    question_image_url=question.question_image_url,
                    question_image_alt_text=question.question_image_alt_text,
                    passage_text=question.passage_text,
                    difficulty=question.difficulty,
                    explanation=question.explanation,
                    marks=question.marks,
                    negative_marks=question.negative_marks,
                    category_slug=category.slug if category else "unknown",
                    category_name=category.name if category else "Unknown",
                    topic_name=topic.name if topic else None,
                    topic_slug=topic.slug if topic else None,
                    options_snapshot=options_snapshot,
                    correct_option_ids=correct_option_ids,
                    correct_numeric_value=question.correct_numeric_value,
                    numeric_tolerance=question.numeric_tolerance,
                )
            )

        await self.db.commit()
        await self.db.refresh(session)
        return await self.get_session_detail(user_id, session.id)

    async def _resolve_category_ids(self, section_slugs: list[str]) -> list[str]:
        if not section_slugs:
            return [c.id for c in await self.categories.list_all()]
        ids = []
        for slug in section_slugs:
            category = await self.categories.get_by_slug(slug)
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown section '{slug}'"
                )
            ids.append(category.id)
        return ids

    async def _resolve_job_context(
        self, user_id: str, payload: TestSessionCreate
    ) -> tuple[str | None, str | None, str | None]:
        if payload.job_id:
            job = await JobRepository(self.db).get_by_id(payload.job_id)
            if job is None:
                return None, None, None
            return None, job.industry, job.title

        if payload.application_id:
            application = await ApplicationRepository(self.db).get_owned(payload.application_id, user_id)
            if application is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
            job: Job | None = None
            if application.job_id:
                job = await JobRepository(self.db).get_by_id(application.job_id)
            # A linked job's industry gives the generator more to match on than the application's
            # freeform role_title alone; job.title is preferred as job_role when available.
            industry = job.industry if job else None
            job_role = (job.title if job else None) or application.role_title
            return None, industry, job_role

        return None, None, None

    # -- fetching / expiry ----------------------------------------------------

    async def _get_owned_or_404(self, user_id: str, session_id: str) -> TestSession:
        session = await self.sessions.get_owned(session_id, user_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test session not found")
        return session

    async def _auto_submit_if_expired(self, session: TestSession) -> TestSession:
        """The backend is the timing authority (spec §18-19): a client can never keep a session
        alive past `expires_at` just by not calling submit. Checked on every read/write."""
        if (
            session.status == TestStatus.IN_PROGRESS
            and session.expires_at is not None
            and datetime.now(timezone.utc) >= _as_aware_utc(session.expires_at)
        ):
            await self._grade_and_close(session, auto_submitted=True)
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def get_session_detail(self, user_id: str, session_id: str) -> TestSessionDetailOut:
        session = await self._get_owned_or_404(user_id, session_id)
        session = await self._auto_submit_if_expired(session)

        session_questions = await self.sessions.get_session_questions(session_id)
        answers = {a.session_question_id: a for a in await self.sessions.get_answers_for_session(session_id)}

        is_submitted = session.status in (TestStatus.SUBMITTED, TestStatus.AUTO_SUBMITTED)
        questions_out = []
        for sq in session_questions:
            answer = answers.get(sq.id)
            answer_state = None
            if answer:
                answer_state = SessionAnswerStateOut(
                    selected_option_ids=answer.selected_option_ids,
                    answer_numeric_value=answer.answer_numeric_value,
                    is_flagged=answer.is_flagged,
                )
            questions_out.append(
                SessionQuestionOut(
                    id=sq.id,
                    order_index=sq.order_index,
                    question_text=sq.question_text,
                    question_type=sq.question_type,
                    question_image_url=sq.question_image_url,
                    question_image_alt_text=sq.question_image_alt_text,
                    passage_text=sq.passage_text,
                    difficulty=sq.difficulty,
                    marks=sq.marks,
                    negative_marks=sq.negative_marks,
                    category_name=sq.category_name,
                    topic_name=sq.topic_name,
                    topic_slug=sq.topic_slug,
                    options=[OptionOut(**opt) for opt in (sq.options_snapshot or [])],
                    answer_state=answer_state,
                )
            )

        now = datetime.now(timezone.utc)
        remaining = None
        if session.expires_at is not None and not is_submitted:
            remaining = max(0, int((_as_aware_utc(session.expires_at) - now).total_seconds()))

        base = TestSessionOut.model_validate(session).model_dump()
        base["questions"] = questions_out
        base["server_time"] = now
        base["remaining_seconds"] = remaining
        return TestSessionDetailOut.model_validate(base)

    async def list_for_user(self, user_id: str, *, page: int, page_size: int, status_filter: str | None):
        items, total = await self.sessions.list_for_user(user_id, page=page, page_size=page_size, status=status_filter)
        return [TestSessionOut.model_validate(s) for s in items], total

    # -- answering ------------------------------------------------------------

    async def update_answer(
        self, user_id: str, session_id: str, session_question_id: str, payload: AnswerUpdate
    ) -> SessionQuestionOut:
        session = await self._get_owned_or_404(user_id, session_id)
        session = await self._auto_submit_if_expired(session)
        if session.status != TestStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="This session is no longer in progress."
            )

        sq = await self.sessions.get_session_question(session_id, session_question_id)
        if sq is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in this session")

        answer = await self.sessions.get_answer(session_question_id)
        if answer is None:
            answer = TestAnswer(session_id=session_id, session_question_id=session_question_id)

        if payload.selected_option_ids is not None:
            answer.selected_option_ids = payload.selected_option_ids
        if payload.answer_numeric_value is not None:
            answer.answer_numeric_value = payload.answer_numeric_value
        if payload.time_spent_seconds is not None:
            answer.time_spent_seconds = payload.time_spent_seconds

        await self.sessions.upsert_answer(answer)
        await self.db.commit()

        detail = await self.get_session_detail(user_id, session_id)
        return next(q for q in detail.questions if q.id == session_question_id)

    async def toggle_flag(self, user_id: str, session_id: str, session_question_id: str) -> SessionQuestionOut:
        session = await self._get_owned_or_404(user_id, session_id)
        session = await self._auto_submit_if_expired(session)
        if session.status != TestStatus.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session is no longer in progress.")

        sq = await self.sessions.get_session_question(session_id, session_question_id)
        if sq is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found in this session")

        answer = await self.sessions.get_answer(session_question_id)
        if answer is None:
            answer = TestAnswer(session_id=session_id, session_question_id=session_question_id)
        answer.is_flagged = not answer.is_flagged
        await self.sessions.upsert_answer(answer)
        await self.db.commit()

        detail = await self.get_session_detail(user_id, session_id)
        return next(q for q in detail.questions if q.id == session_question_id)

    # -- submission / grading --------------------------------------------------

    async def submit(self, user_id: str, session_id: str) -> TestResultOut:
        session = await self._get_owned_or_404(user_id, session_id)
        session = await self._auto_submit_if_expired(session)

        if session.status == TestStatus.IN_PROGRESS:
            await self._grade_and_close(session, auto_submitted=False)
            await self.db.commit()
            await self.db.refresh(session)
        elif session.status not in (TestStatus.SUBMITTED, TestStatus.AUTO_SUBMITTED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session cannot be submitted.")

        return await self.get_result(user_id, session_id)

    async def _grade_and_close(self, session: TestSession, *, auto_submitted: bool) -> None:
        session_questions = await self.sessions.get_session_questions(session.id)
        answers = {a.session_question_id: a for a in await self.sessions.get_answers_for_session(session.id)}

        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        raw_score = 0.0
        section_totals: dict[str, dict[str, int]] = {}

        for sq in session_questions:
            answer = answers.get(sq.id)
            section_totals.setdefault(sq.category_name, {"correct": 0, "total": 0})
            section_totals[sq.category_name]["total"] += 1

            is_correct, marks_awarded = _grade_answer(sq, answer)
            if answer is not None:
                answer.is_correct = is_correct
                answer.marks_awarded = marks_awarded
                self.db.add(answer)

            if is_correct is None:
                unanswered_count += 1
            elif is_correct:
                correct_count += 1
                section_totals[sq.category_name]["correct"] += 1
                raw_score += marks_awarded
            else:
                incorrect_count += 1
                raw_score += marks_awarded  # marks_awarded is negative (or zero) here

        total_marks = session.total_marks or 1.0
        percentage = (raw_score / total_marks) * 100 if total_marks else 0.0

        now = datetime.now(timezone.utc)
        started_at = _as_aware_utc(session.started_at) if session.started_at else now
        time_used = int((now - started_at).total_seconds())
        if session.time_limit_seconds is not None:
            time_used = min(time_used, session.time_limit_seconds)

        session.status = TestStatus.AUTO_SUBMITTED if auto_submitted else TestStatus.SUBMITTED
        session.submitted_at = now
        session.auto_submitted = auto_submitted
        session.score = raw_score
        session.percentage = percentage
        session.correct_count = correct_count
        session.incorrect_count = incorrect_count
        session.unanswered_count = unanswered_count
        session.time_used_seconds = time_used
        session.section_breakdown = {
            name: {
                "correct": stats["correct"],
                "total": stats["total"],
                "percentage": round((stats["correct"] / stats["total"]) * 100, 1) if stats["total"] else 0.0,
            }
            for name, stats in section_totals.items()
        }
        self.db.add(session)

    async def get_result(self, user_id: str, session_id: str) -> TestResultOut:
        session = await self._get_owned_or_404(user_id, session_id)
        if session.status not in (TestStatus.SUBMITTED, TestStatus.AUTO_SUBMITTED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session hasn't been submitted yet.")

        return TestResultOut(
            session_id=session.id,
            status=session.status,
            score=session.score or 0.0,
            total_marks=session.total_marks,
            percentage=session.percentage or 0.0,
            correct_count=session.correct_count or 0,
            incorrect_count=session.incorrect_count or 0,
            unanswered_count=session.unanswered_count or 0,
            time_used_seconds=session.time_used_seconds,
            time_limit_seconds=session.time_limit_seconds,
            auto_submitted=session.auto_submitted,
            section_breakdown=session.section_breakdown or {},
            performance_label=performance_label(session.percentage or 0.0),
        )

    # -- review -----------------------------------------------------------------

    async def get_review(self, user_id: str, session_id: str) -> ReviewOut:
        session = await self._get_owned_or_404(user_id, session_id)
        if session.status not in (TestStatus.SUBMITTED, TestStatus.AUTO_SUBMITTED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Review is available only after submitting."
            )

        session_questions = await self.sessions.get_session_questions(session_id)
        answers = {a.session_question_id: a for a in await self.sessions.get_answers_for_session(session_id)}

        questions_out = []
        for sq in session_questions:
            answer = answers.get(sq.id)
            correct_ids = set(sq.correct_option_ids or [])
            options = [
                ReviewOptionOut(**opt, is_correct=opt["id"] in correct_ids) for opt in (sq.options_snapshot or [])
            ]
            questions_out.append(
                ReviewQuestionOut(
                    id=sq.id,
                    order_index=sq.order_index,
                    question_text=sq.question_text,
                    question_type=sq.question_type,
                    question_image_url=sq.question_image_url,
                    question_image_alt_text=sq.question_image_alt_text,
                    passage_text=sq.passage_text,
                    difficulty=sq.difficulty,
                    category_name=sq.category_name,
                    topic_name=sq.topic_name,
                    topic_slug=sq.topic_slug,
                    options=options,
                    selected_option_ids=answer.selected_option_ids if answer else None,
                    answer_numeric_value=answer.answer_numeric_value if answer else None,
                    correct_numeric_value=sq.correct_numeric_value,
                    is_correct=answer.is_correct if answer else None,
                    marks_awarded=answer.marks_awarded if answer else None,
                    explanation=sq.explanation,
                    time_spent_seconds=answer.time_spent_seconds if answer else None,
                )
            )

        return ReviewOut(session_id=session.id, questions=questions_out)

    # -- analytics / recommendations ---------------------------------------------

    async def get_analytics(self, user_id: str) -> AptitudeAnalyticsOut:
        sessions = await self.sessions.list_submitted_for_user(user_id)

        category_stats: dict[str, dict[str, int]] = {}
        topic_stats: dict[str, dict[str, object]] = {}
        total_questions_answered = 0
        total_time_spent = 0
        time_tracked_count = 0
        scores = [s.percentage for s in sessions if s.percentage is not None]

        for session in sessions:
            session_questions = await self.sessions.get_session_questions(session.id)
            answers = {a.session_question_id: a for a in await self.sessions.get_answers_for_session(session.id)}
            for sq in session_questions:
                answer = answers.get(sq.id)
                if answer is None or answer.is_correct is None:
                    continue
                total_questions_answered += 1
                if answer.time_spent_seconds:
                    total_time_spent += answer.time_spent_seconds
                    time_tracked_count += 1

                cat = category_stats.setdefault(sq.category_name, {"attempted": 0, "correct": 0})
                cat["attempted"] += 1
                if answer.is_correct:
                    cat["correct"] += 1

                if sq.topic_name:
                    topic = topic_stats.setdefault(
                        sq.topic_name,
                        {"category_name": sq.category_name, "topic_slug": sq.topic_slug, "attempted": 0, "correct": 0},
                    )
                    topic["attempted"] += 1
                    if answer.is_correct:
                        topic["correct"] += 1

        by_category = {
            name: CategoryStat(
                attempted=stats["attempted"],
                correct=stats["correct"],
                percentage=round((stats["correct"] / stats["attempted"]) * 100, 1) if stats["attempted"] else 0.0,
            )
            for name, stats in category_stats.items()
        }
        by_topic = {
            name: TopicStat(
                category_name=stats["category_name"],
                topic_slug=stats["topic_slug"],
                attempted=stats["attempted"],
                correct=stats["correct"],
                percentage=round((stats["correct"] / stats["attempted"]) * 100, 1) if stats["attempted"] else 0.0,
            )
            for name, stats in topic_stats.items()
        }

        return AptitudeAnalyticsOut(
            tests_completed=len(sessions),
            questions_answered=total_questions_answered,
            average_score=round(sum(scores) / len(scores), 1) if scores else None,
            best_score=round(max(scores), 1) if scores else None,
            average_time_per_question_seconds=(
                round(total_time_spent / time_tracked_count, 1) if time_tracked_count else None
            ),
            by_category=by_category,
            by_topic=by_topic,
        )

    async def get_recommendations(self, user_id: str) -> RecommendationsOut:
        analytics = await self.get_analytics(user_id)
        weak = [
            WeakTopicOut(
                topic_name=name,
                topic_slug=stat.topic_slug,
                category_name=stat.category_name,
                accuracy=stat.percentage,
                attempted=stat.attempted,
            )
            for name, stat in analytics.by_topic.items()
            if stat.attempted >= MIN_ATTEMPTS_FOR_TOPIC_RECOMMENDATION and stat.percentage < WEAK_TOPIC_ACCURACY_THRESHOLD
        ]
        weak.sort(key=lambda w: w.accuracy)
        return RecommendationsOut(
            weak_topics=weak[:MAX_WEAK_TOPICS_RETURNED],
            min_attempts_required=MIN_ATTEMPTS_FOR_TOPIC_RECOMMENDATION,
        )


def _grade_answer(sq: TestSessionQuestion, answer: TestAnswer | None) -> tuple[bool | None, float]:
    if answer is None:
        return None, 0.0

    if sq.question_type == QuestionType.NUMERIC:
        if answer.answer_numeric_value is None:
            return None, 0.0
        correct = abs(answer.answer_numeric_value - (sq.correct_numeric_value or 0.0)) <= sq.numeric_tolerance
    else:
        if not answer.selected_option_ids:
            return None, 0.0
        correct = set(answer.selected_option_ids) == set(sq.correct_option_ids or [])

    marks = sq.marks if correct else -sq.negative_marks
    return correct, marks


def _as_aware_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip even for DateTime(timezone=True) columns; Postgres
    doesn't. Every datetime this app writes is UTC, so treat a naive value as UTC rather than
    crash comparing aware/naive (same fix as job_service._is_publicly_visible)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
