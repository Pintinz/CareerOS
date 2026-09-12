"""Seeds the interview question bank for local development (Phase 7 spec §6/§34).

Every question is fictional-but-genuinely-useful practice content, flagged `is_demo=True` like
every other seeded record in this project. `answer_guidance`/`evaluation_points` are deterministic,
hand-written structured content — never AI-generated, never presented as an employer's official
guidance (spec §13/§35). Safe to re-run: skips seeding if any demo interview question already exists.

Usage:
    cd backend && python -m scripts.seed_interview_questions
"""

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import admin_user, application, company, job, profile, user  # noqa: F401  (resolves cross-model FKs)
from app.models.interview import (
    InterviewDifficulty,
    InterviewQuestion,
    InterviewQuestionCategory,
    InterviewTopic,
)
from app.models.job import ExperienceLevel

CATEGORIES = [
    dict(name="HR / General", slug="hr_general", description="General fit, motivation, and standard HR screening questions."),
    dict(name="Behavioral", slug="behavioral", description="Past-experience questions best answered with a STAR story."),
    dict(name="Technical", slug="technical", description="Role- and field-specific technical knowledge questions."),
    dict(name="Company-Specific", slug="company_specific", description="Questions about the target company and why the candidate wants to join it."),
    dict(name="Job-Specific", slug="job_specific", description="Questions tailored to the specific role's day-to-day responsibilities."),
    dict(name="Safety", slug="safety", description="Safety awareness, procedures, and incident-response questions."),
    dict(name="Leadership", slug="leadership", description="Leading, mentoring, and influencing others."),
    dict(name="Management", slug="management", description="Managing people, performance, and priorities."),
    dict(name="Situational", slug="situational", description="Hypothetical 'what would you do' scenario questions."),
    dict(name="Career Motivation", slug="career_motivation", description="Career goals, motivation, and long-term direction."),
]

TOPICS = [
    # Slugs deliberately match app/interview/job_role_topic_map.py's bare topic slugs exactly so
    # job-specific generation can actually find them by topic.
    ("technical", "Pumps", "pumps", "Mechanical Engineering", "Oil & Gas"),
    ("technical", "Valves", "valves", "Mechanical Engineering", "Oil & Gas"),
    ("technical", "DCS", "dcs", "Process Operations", "Oil & Gas"),
    ("technical", "SCADA", "scada", "Electrical Engineering", "Oil & Gas"),
    ("technical", "LOTO", "loto", None, None),
    ("technical", "P&IDs", "p-and-ids", "Process Operations", "Oil & Gas"),
    ("technical", "Process Safety", "process-safety", "Process Operations", "Oil & Gas"),
    ("technical", "Troubleshooting", "troubleshooting", "Mechanical Engineering", None),
    ("technical", "SQL & Databases", "sql-scenarios", "Data Analysis", None),
    ("technical", "System Design", "system-design", "Software Engineering", None),
    ("job_specific", "Process Monitoring", "process-monitoring", "Process Operations", "Oil & Gas"),
    ("job_specific", "Shift Handover", "shift-handover", "Process Operations", "Oil & Gas"),
    ("job_specific", "Emergency Response", "emergency-response", "Process Operations", "Oil & Gas"),
    ("job_specific", "Abnormal Conditions", "abnormal-conditions", "Process Operations", "Oil & Gas"),
]

E, M, H, X = InterviewDifficulty.EASY, InterviewDifficulty.MEDIUM, InterviewDifficulty.HARD, InterviewDifficulty.EXPERT

QUESTIONS: list[dict] = []


def q(
    category,
    text,
    *,
    topic=None,
    difficulty=M,
    experience_level=None,
    assessing="",
    includes=None,
    mistakes=None,
    concepts=None,
    follow_up=None,
    star_tags=None,
    eval_points=None,
):
    QUESTIONS.append(
        dict(
            category=category,
            topic=topic,
            difficulty=difficulty,
            experience_level=experience_level,
            question_text=text,
            answer_guidance={
                "assessing": assessing,
                "strong_answer_includes": includes or [],
                "common_mistakes": mistakes or [],
                "technical_concepts": concepts or [],
            },
            evaluation_points=eval_points or (includes or [])[:3],
            follow_up_prompt=follow_up,
            star_tags=star_tags or [],
        )
    )


# ---------------------------------------------------------------------------
# HR / General (25+)
# ---------------------------------------------------------------------------

q("hr_general", "Tell me about yourself.", difficulty=E,
  assessing="How well the candidate summarizes their background and connects it to the role.",
  includes=["A brief, relevant career summary", "Why they're a fit for this specific role", "A confident, concise delivery"],
  mistakes=["Reciting the entire resume", "Rambling with no clear structure", "Oversharing unrelated personal details"],
  follow_up="What part of your background is most relevant to this role?")
q("hr_general", "Why do you want this job?", difficulty=E,
  assessing="Genuine motivation and whether they've researched the role.",
  includes=["A specific reason tied to the role or company", "Alignment between their goals and the position", "Enthusiasm without exaggeration"],
  mistakes=["Generic answers that could apply to any job", "Focusing only on salary or benefits"])
q("hr_general", "What are your strengths?", difficulty=E,
  assessing="Self-awareness and relevance of the strength to the job.",
  includes=["A strength directly relevant to the role", "A specific example demonstrating it"],
  mistakes=["Listing generic buzzwords with no evidence", "Choosing a strength irrelevant to the job"])
q("hr_general", "What is your greatest weakness?", difficulty=M,
  assessing="Honesty and whether the candidate is actively improving.",
  includes=["A real, believable weakness", "Concrete steps taken to improve it"],
  mistakes=["A humble-brag disguised as a weakness (e.g. 'I work too hard')", "Naming a weakness critical to the job"])
q("hr_general", "Why are you leaving your current job?", difficulty=M,
  assessing="Professionalism and whether the reason is constructive rather than negative.",
  includes=["A forward-looking, positive reason", "No disparagement of the previous employer"],
  mistakes=["Speaking negatively about a former employer or manager"])
q("hr_general", "Where do you see yourself in five years?", difficulty=M,
  assessing="Whether their career direction aligns with what this role can offer.",
  includes=["A realistic, role-relevant growth path", "Some flexibility rather than an overly rigid plan"])
q("hr_general", "Why should we hire you?", difficulty=M,
  assessing="Ability to summarize their unique value proposition confidently.",
  includes=["A clear, specific value proposition", "Evidence tied to the role's requirements"],
  mistakes=["Restating the resume without synthesis", "Comparing themselves negatively to other candidates"])
q("hr_general", "What do you know about our company?", difficulty=E,
  assessing="Whether the candidate did basic research before the interview.",
  includes=["Accurate, specific facts about the company", "A connection between the company's work and their own interests"],
  mistakes=["Vague or clearly unresearched answers"])
q("hr_general", "How do you handle stress and pressure?", difficulty=M,
  assessing="Coping strategies and self-regulation under pressure.",
  includes=["A concrete coping strategy", "A real example of managing pressure successfully"], star_tags=["pressure"])
q("hr_general", "What motivates you at work?", difficulty=E,
  assessing="Alignment between intrinsic motivation and the nature of the role.",
  includes=["A genuine, specific motivator", "Connection to the day-to-day realities of this job"])
q("hr_general", "Describe your ideal work environment.", difficulty=E,
  assessing="Cultural fit with the team/company.",
  includes=["A description consistent with the company's actual environment"])
q("hr_general", "What salary range are you expecting?", difficulty=M,
  assessing="Preparedness and negotiation reasonableness.",
  includes=["A researched, realistic range", "Openness to discussion"],
  mistakes=["Refusing to answer at all", "An answer wildly out of market range"])
q("hr_general", "How would your previous manager describe you?", difficulty=M,
  assessing="Self-awareness and consistency with how references might describe them.",
  includes=["Specific traits with brief supporting evidence"])
q("hr_general", "What are you looking for in your next role?", difficulty=E,
  assessing="Whether their priorities match what the role actually offers.",
  includes=["Priorities that align with the role's realities"])
q("hr_general", "How do you prioritize your work when everything feels urgent?", difficulty=M,
  assessing="A structured approach to prioritization under load.",
  includes=["A named method (e.g. urgency vs. impact)", "A concrete example"], star_tags=["pressure", "decision_making"])
q("hr_general", "Tell me about a time you had to learn something new quickly.", difficulty=M,
  assessing="Adaptability and learning agility.",
  includes=["A specific learning situation", "The method used to learn quickly", "The outcome"], star_tags=["problem_solving"])
q("hr_general", "What questions do you have for us?", difficulty=E,
  assessing="Genuine engagement and preparation.",
  includes=["Specific, thoughtful questions about the role or team"],
  mistakes=["Saying 'no questions'", "Asking only about pay/perks"])
q("hr_general", "How do you handle receiving critical feedback?", difficulty=M,
  assessing="Openness to feedback and growth mindset.",
  includes=["A real example of acting on feedback", "A non-defensive tone"])
q("hr_general", "What does work-life balance mean to you?", difficulty=E,
  assessing="Realistic expectations aligned with the role's demands.",
  includes=["A balanced, realistic perspective"])
q("hr_general", "Describe a time you disagreed with a company policy. What did you do?", difficulty=H,
  assessing="Professional judgment when navigating disagreement with authority/policy.",
  includes=["Raised the concern through appropriate channels", "Ultimately respected the decision or process"], star_tags=["conflict", "decision_making"])
q("hr_general", "What's something you're currently working on improving about yourself?", difficulty=E,
  assessing="Self-awareness and commitment to growth.",
  includes=["A specific, believable area of growth", "Concrete action being taken"])
q("hr_general", "How do you stay organized when managing multiple priorities?", difficulty=M,
  assessing="Personal organization systems.",
  includes=["A concrete system or tool", "An example of it working"])
q("hr_general", "Tell me about a time you made a mistake at work. How did you handle it?", difficulty=M,
  assessing="Accountability and recovery from mistakes.",
  includes=["Ownership without excessive blame-shifting", "What was learned and changed"], star_tags=["failure_lesson"])
q("hr_general", "What type of management style do you work best under?", difficulty=E,
  assessing="Self-awareness and compatibility with the team's actual management style.",
  includes=["A specific style with reasoning"])
q("hr_general", "Why is there a gap in your employment history?", difficulty=M,
  assessing="Comfort and honesty discussing employment gaps.",
  includes=["A direct, honest explanation", "What was done during the gap (if relevant)"])
q("hr_general", "How would you handle a situation where you strongly disagree with your manager's decision?", difficulty=H,
  assessing="Professional disagreement and escalation judgment.",
  includes=["Raising the concern respectfully and privately", "Supporting the final decision once made"], star_tags=["conflict"])
q("hr_general", "What are you passionate about outside of work?", difficulty=E,
  assessing="Well-roundedness; rarely a disqualifying question either way.",
  includes=["An authentic, brief answer"])

# ---------------------------------------------------------------------------
# Behavioral (30+)
# ---------------------------------------------------------------------------

q("behavioral", "Tell me about a time you worked effectively as part of a team.", difficulty=E,
  assessing="Teamwork and collaborative contribution.",
  includes=["A specific team situation", "Their individual contribution", "The team outcome"], star_tags=["teamwork"])
q("behavioral", "Describe a time you had a conflict with a coworker. How did you resolve it?", difficulty=M,
  assessing="Conflict-resolution skills and professionalism.",
  includes=["The root cause of the conflict", "Steps taken to resolve it directly and respectfully", "The resolution"], star_tags=["conflict"])
q("behavioral", "Tell me about a time you solved a difficult problem.", difficulty=M,
  assessing="Analytical thinking and problem-solving approach.",
  includes=["The problem's complexity", "The systematic approach used", "The measurable result"], star_tags=["problem_solving", "equipment_failure", "process_improvement"])
q("behavioral", "Describe a time you failed at something. What did you learn?", difficulty=H,
  assessing="Accountability and ability to learn from failure.",
  includes=["A genuine failure, not a disguised success", "Honest reflection", "A concrete lesson applied afterward"], star_tags=["failure_lesson"])
q("behavioral", "Tell me about a time you went above and beyond for a customer or stakeholder.", difficulty=M,
  assessing="Customer/stakeholder orientation.",
  includes=["The extra effort taken", "The impact on the customer/stakeholder"], star_tags=["customer"])
q("behavioral", "Describe a time you had to persuade someone to see things your way.", difficulty=M,
  assessing="Influence and persuasion skills.",
  includes=["The approach used to build the case", "How resistance was addressed", "The outcome"], star_tags=["communication", "decision_making"])
q("behavioral", "Tell me about a time you had to meet a tight deadline.", difficulty=M,
  assessing="Time management and performance under pressure.",
  includes=["How priorities were managed", "Whether the deadline was met and how"], star_tags=["pressure"])
q("behavioral", "Describe a situation where you had to adapt to a significant change at work.", difficulty=M,
  assessing="Adaptability and resilience.",
  includes=["The nature of the change", "How they adjusted their approach", "The outcome"], star_tags=["pressure", "decision_making"])
q("behavioral", "Tell me about a time you took initiative without being asked.", difficulty=M,
  assessing="Proactivity and ownership.",
  includes=["The opportunity they identified", "The action taken independently", "The result"], star_tags=["innovation", "achievement"])
q("behavioral", "Describe a time you had to give difficult feedback to someone.", difficulty=H,
  assessing="Communication skill in a sensitive situation.",
  includes=["A respectful, direct approach", "The outcome of the conversation"], star_tags=["communication", "leadership"])
q("behavioral", "Tell me about your proudest professional achievement.", difficulty=E,
  assessing="What the candidate values and how they measure success.",
  includes=["A specific, measurable achievement", "Their personal role in it"], star_tags=["achievement"])
q("behavioral", "Describe a time you had to work with someone difficult.", difficulty=M,
  assessing="Interpersonal skill and professionalism under friction.",
  includes=["A specific behavior, not a personality attack", "How the working relationship was managed"], star_tags=["conflict", "teamwork"])
q("behavioral", "Tell me about a time you improved a process.", difficulty=M,
  assessing="Continuous-improvement mindset.",
  includes=["The inefficiency identified", "The change implemented", "The measurable improvement"], star_tags=["process_improvement"])
q("behavioral", "Describe a time you had to make a decision with incomplete information.", difficulty=H,
  assessing="Judgment under uncertainty.",
  includes=["The reasoning process used", "How risk was managed", "The outcome"], star_tags=["decision_making", "pressure"])
q("behavioral", "Tell me about a time you had to balance multiple competing priorities.", difficulty=M,
  assessing="Prioritization skill under real constraints.",
  includes=["The competing demands", "The prioritization method used", "The outcome"])
q("behavioral", "Describe a time your work was criticized. How did you respond?", difficulty=M,
  assessing="Resilience and openness to feedback.",
  includes=["A non-defensive response", "Concrete changes made afterward"], star_tags=["failure_lesson"])
q("behavioral", "Tell me about a time you had to quickly build trust with a new team.", difficulty=M,
  assessing="Interpersonal effectiveness in unfamiliar situations.",
  includes=["Specific actions taken to build credibility/trust", "The outcome"], star_tags=["teamwork", "communication"])
q("behavioral", "Describe a time you exceeded a target or goal.", difficulty=M,
  assessing="Drive and performance orientation.",
  includes=["The target", "The actions that led to exceeding it", "The measurable margin"], star_tags=["achievement"])
q("behavioral", "Tell me about a time you had to say no to a request.", difficulty=H,
  assessing="Assertiveness balanced with professionalism.",
  includes=["Clear reasoning for declining", "How the relationship was preserved"], star_tags=["decision_making", "communication"])
q("behavioral", "Describe a time you worked with limited resources to get a job done.", difficulty=M,
  assessing="Resourcefulness.",
  includes=["The constraint", "The creative solution", "The outcome"], star_tags=["problem_solving", "innovation"])
q("behavioral", "Tell me about a time you had to coordinate across multiple departments or teams.", difficulty=H,
  assessing="Cross-functional collaboration skill.",
  includes=["The coordination challenge", "How alignment was achieved", "The result"], star_tags=["teamwork", "communication"])
q("behavioral", "Describe a time you identified a risk before it became a problem.", difficulty=H,
  assessing="Foresight and risk awareness.",
  includes=["How the risk was spotted", "The preventive action taken"], star_tags=["problem_solving", "decision_making"])
q("behavioral", "Tell me about a time you had to explain something technical to a non-technical audience.", difficulty=M,
  assessing="Communication clarity across audiences.",
  includes=["How the explanation was simplified", "Confirmation the audience understood"], star_tags=["communication"])
q("behavioral", "Describe a time you volunteered for a task outside your normal responsibilities.", difficulty=E,
  assessing="Willingness to contribute beyond the job description.",
  includes=["The task taken on", "Why they volunteered", "The outcome"], star_tags=["innovation", "achievement"])
q("behavioral", "Tell me about a time you had to recover from a significant setback.", difficulty=H,
  assessing="Resilience and recovery.",
  includes=["The setback", "The recovery actions", "The eventual outcome"], star_tags=["pressure", "failure_lesson"])
q("behavioral", "Describe a time you mentored or helped a colleague develop a skill.", difficulty=M,
  assessing="Willingness and ability to develop others.",
  includes=["The specific help provided", "The colleague's resulting improvement"], star_tags=["leadership", "teamwork"])
q("behavioral", "Tell me about a time you had to deliver results with very little supervision.", difficulty=M,
  assessing="Independence and self-direction.",
  includes=["The scope of autonomy", "How they stayed on track", "The result"], star_tags=["achievement", "decision_making"])
q("behavioral", "Describe a time you had to change your approach midway through a project.", difficulty=H,
  assessing="Flexibility and course-correction ability.",
  includes=["Why the change was needed", "How it was executed", "The outcome"], star_tags=["decision_making", "process_improvement"])
q("behavioral", "Tell me about a time you used data to support a decision.", difficulty=M,
  assessing="Data-informed decision-making.",
  includes=["The data used", "The decision it informed", "The outcome"], star_tags=["decision_making"])
q("behavioral", "Describe a time you had to stay motivated during a long, low-visibility project.", difficulty=M,
  assessing="Sustained motivation and follow-through.",
  includes=["What kept them engaged", "How progress was maintained"], star_tags=["pressure", "achievement"])

# ---------------------------------------------------------------------------
# Technical (40+): Mechanical/Process, Data/Analytics, Software/Technology, General operations
# ---------------------------------------------------------------------------

q("technical", "Walk me through how a centrifugal pump works.", topic="pumps", difficulty=M,
  assessing="Fundamental understanding of rotating equipment.",
  concepts=["Impeller", "Kinetic-to-pressure energy conversion", "NPSH", "Cavitation"],
  includes=["A clear step-by-step explanation", "Mention of cavitation risk"])
q("technical", "What causes pump cavitation and how would you prevent it?", topic="pumps", difficulty=H,
  assessing="Practical troubleshooting knowledge of a common failure mode.",
  concepts=["NPSH available vs. required", "Suction pressure", "Fluid temperature"],
  includes=["Identifying insufficient NPSH as the root cause", "Prevention steps"])
q("technical", "Explain the difference between a gate valve and a globe valve.", topic="valves", difficulty=M,
  assessing="Valve selection knowledge for the right application.",
  concepts=["On/off vs. throttling service", "Flow resistance"],
  includes=["Gate = on/off, globe = throttling", "A real-world example of each"])
q("technical", "What is the purpose of a DCS in a process plant?", topic="dcs", difficulty=M,
  assessing="Understanding of process control architecture.",
  concepts=["Distributed control", "Centralized monitoring", "Control loops"],
  includes=["Centralized monitoring with distributed processing"])
q("technical", "How does SCADA differ from a DCS?", topic="scada", difficulty=H,
  assessing="Distinguishing supervisory control from distributed control.",
  concepts=["Geographically dispersed assets", "Telemetry", "Centralized control room"],
  includes=["SCADA for dispersed/remote assets, DCS for a single facility's continuous process"])
q("technical", "Walk me through the LOTO process and why each step matters.", topic="loto", difficulty=M,
  assessing="Practical safety-critical procedural knowledge.",
  concepts=["Isolation", "Lockout", "Tagout", "Verification of zero energy"],
  includes=["Every step in the correct order", "Why skipping verification is dangerous"], star_tags=["safety"])
q("technical", "What information does a P&ID show that a general process flow diagram doesn't?", topic="p-and-ids", difficulty=M,
  assessing="Reading and interpreting engineering drawings.",
  concepts=["Instrumentation", "Piping specifications", "Control loops"],
  includes=["Instrumentation and control detail beyond the high-level process flow"])
q("technical", "What are the key elements of a process safety management program?", topic="process-safety", difficulty=H,
  assessing="Breadth of process safety knowledge.",
  concepts=["Hazard analysis", "Management of change", "Mechanical integrity", "Incident investigation"],
  includes=["At least 3 concrete PSM elements"], star_tags=["safety"])
q("technical", "Describe your general approach to troubleshooting equipment that suddenly stops working.", topic="troubleshooting", difficulty=M,
  assessing="Structured troubleshooting methodology.",
  concepts=["Root cause analysis", "Isolating variables", "Verifying the fix"],
  includes=["A structured, step-by-step method rather than guessing"], star_tags=["equipment_failure", "problem_solving"])
q("technical", "What steps would you take if you noticed an abnormal reading on a critical process parameter?", difficulty=H,
  assessing="Response discipline under a real operational anomaly.",
  concepts=["Verify instrumentation", "Cross-check with other indicators", "Escalate per procedure"],
  includes=["Verify before reacting", "Follow escalation procedure", "Communicate clearly to the team"], star_tags=["safety", "decision_making"])
q("technical", "Write a SQL query to find the second-highest salary in an employee table.", topic="sql-scenarios", difficulty=H,
  assessing="Practical SQL problem-solving.",
  concepts=["Subqueries", "LIMIT/OFFSET or window functions", "Handling ties"],
  includes=["A correct, working query", "Awareness of tie-handling edge cases"])
q("technical", "What's the difference between an INNER JOIN and a LEFT JOIN?", topic="sql-scenarios", difficulty=E,
  assessing="Core relational database knowledge.",
  concepts=["Matched rows only vs. all left-table rows"],
  includes=["A correct, concise explanation with an example"])
q("technical", "How would you design a URL-shortening service?", topic="system-design", difficulty=X,
  assessing="System design fundamentals at a senior level.",
  concepts=["Hashing/encoding scheme", "Database choice", "Read/write scaling", "Caching"],
  includes=["A working high-level architecture", "Consideration of scale and collision handling"])
q("technical", "What's the difference between a process and a thread?", topic="system-design", difficulty=M,
  assessing="Core computer-science fundamentals.",
  concepts=["Memory isolation", "Shared memory space", "Context switching cost"],
  includes=["Correct distinction with a practical example"])
q("technical", "How do you approach debugging a production issue you can't reproduce locally?", difficulty=H,
  assessing="Real-world debugging methodology.",
  concepts=["Logging", "Monitoring/observability", "Reproducing via staging data"],
  includes=["A systematic approach using logs/metrics rather than guesswork"], star_tags=["equipment_failure", "problem_solving"])
q("technical", "What is the difference between correlation and causation, and why does it matter in data analysis?", difficulty=M,
  assessing="Statistical reasoning fundamentals.",
  concepts=["Confounding variables", "Controlled experiments"],
  includes=["A clear distinction with a concrete example of a spurious correlation"])
q("technical", "How would you explain a complex data finding to a non-technical stakeholder?", difficulty=M,
  assessing="Communication of technical results.",
  includes=["Simplification without losing accuracy", "Use of visuals or analogies"], star_tags=["communication"])
q("technical", "What is a heat exchanger and why is counter-current flow generally preferred?", difficulty=H,
  concepts=["Counter-current vs. co-current flow", "Temperature gradient", "Heat transfer efficiency"],
  assessing="Thermal equipment fundamentals.",
  includes=["Correct explanation of why counter-current is more efficient"])
q("technical", "What would you check first if a pressure gauge reading seems inconsistent with other instruments?", difficulty=M,
  assessing="Instrumentation troubleshooting instinct.",
  concepts=["Calibration", "Instrument fault vs. real process condition"],
  includes=["Check calibration/instrument health before assuming a real process upset"])
q("technical", "Explain the concept of preventive vs. predictive maintenance.", difficulty=M,
  concepts=["Scheduled intervals", "Condition monitoring", "Failure prediction"],
  assessing="Maintenance strategy knowledge.",
  includes=["Clear distinction with an example of each"])
q("technical", "What is a P95 latency metric and why might it matter more than average latency?", topic="system-design", difficulty=H,
  assessing="Understanding of performance metrics beyond simple averages.",
  concepts=["Percentiles", "Tail latency", "User experience impact"],
  includes=["Explains that averages can hide poor experiences for a meaningful share of users"])
q("technical", "How would you verify a piece of rotating equipment is safe to restart after maintenance?", topic="loto", difficulty=H,
  assessing="Safety-first operational discipline.",
  concepts=["LOTO removal sequence", "Pre-start checks", "Isolation verification"],
  includes=["A clear, ordered checklist rather than a vague answer"], star_tags=["safety"])
q("technical", "What's the purpose of instrumentation calibration and how often should it typically occur?", difficulty=M,
  concepts=["Drift", "Accuracy", "Calibration schedule"],
  assessing="Instrumentation maintenance knowledge.",
  includes=["Explains drift and the need for periodic calibration"])
q("technical", "Describe the basic principle behind a separator vessel in an oil and gas facility.", difficulty=M,
  concepts=["Gravity separation", "Retention time", "Gas/liquid interface"],
  assessing="Process equipment fundamentals.",
  includes=["Correct explanation of gravity-based phase separation"])
q("technical", "What's the difference between SQL and NoSQL databases, and when would you choose each?", topic="sql-scenarios", difficulty=M,
  concepts=["Schema flexibility", "ACID transactions", "Horizontal scaling"],
  assessing="Database architecture judgment.",
  includes=["A correct tradeoff-based answer, not a one-size-fits-all opinion"])
q("technical", "How do you ensure code quality when working under a tight deadline?", topic="system-design", difficulty=M,
  assessing="Balancing speed and quality.",
  includes=["Tests for critical paths", "Code review discipline maintained even under pressure"])
q("technical", "What is root cause analysis and how do you approach it?", difficulty=M,
  concepts=["5 Whys", "Fishbone diagram", "Corrective vs. preventive action"],
  assessing="Structured problem-solving methodology.",
  includes=["A named method and an example of applying it"], star_tags=["problem_solving", "equipment_failure"])
q("technical", "What key performance indicators would you track for a production line?", difficulty=M,
  concepts=["Throughput", "Downtime", "First-pass yield"],
  assessing="Operational metrics literacy.",
  includes=["At least 2 relevant, concrete KPIs"])
q("technical", "How would you handle a situation where a required safety inspection was overdue?", topic="process-safety", difficulty=H,
  assessing="Safety-first prioritization even under production pressure.",
  includes=["Escalate immediately rather than proceeding", "Never bypass safety for schedule"], star_tags=["safety", "decision_making"])
q("technical", "What is the difference between accuracy and precision in a measurement context?", difficulty=M,
  concepts=["Systematic vs. random error"],
  assessing="Measurement fundamentals.",
  includes=["A clear, correct distinction with an example"])
q("technical", "Explain what 'defense in depth' means in a safety or security context.", difficulty=H,
  concepts=["Layered protection", "No single point of failure"],
  assessing="Systems-level safety/security thinking.",
  includes=["Multiple independent layers of protection explained clearly"])
q("technical", "What would you do if you found a discrepancy between two data sources that should match?", difficulty=M,
  assessing="Data quality troubleshooting instinct.",
  includes=["Investigate the source of truth before acting", "Document the discrepancy"], star_tags=["problem_solving"])
q("technical", "What is version control and why does it matter for a team?", topic="system-design", difficulty=E,
  concepts=["Git", "Branching", "Collaboration history"],
  assessing="Basic collaborative software development literacy.",
  includes=["Explains traceability and safe collaboration"])
q("technical", "How would you approach automating a manual, repetitive process?", difficulty=M,
  assessing="Process-improvement and automation mindset.",
  includes=["Identify the repetitive steps", "Justify the automation with time/error savings"], star_tags=["process_improvement", "innovation"])
q("technical", "What is the purpose of a control loop in process automation, and what are its basic components?", topic="dcs", difficulty=H,
  concepts=["Sensor", "Controller", "Final control element", "Setpoint", "Feedback"],
  assessing="Process control fundamentals.",
  includes=["All major components named correctly"])
q("technical", "How do you decide when a technical problem needs to be escalated versus solved independently?", difficulty=M,
  assessing="Judgment about scope and safety of independent action.",
  includes=["Clear criteria (safety, scope, authority) for escalation"], star_tags=["decision_making"])
q("technical", "What is the difference between a false positive and a false negative, and why does the distinction matter operationally?", difficulty=H,
  concepts=["Type I vs. Type II error", "Cost asymmetry"],
  assessing="Statistical/risk reasoning applied to real decisions.",
  includes=["Correct definitions plus a real cost tradeoff example"])
q("technical", "Explain what 'single point of failure' means and how you'd identify one in a system.", topic="system-design", difficulty=H,
  assessing="Reliability engineering thinking.",
  includes=["Correct definition", "A method for identifying one (e.g. dependency mapping)"])
q("technical", "What steps would you take before performing maintenance on equipment that's still running?", topic="loto", difficulty=M,
  assessing="Safety procedure sequencing.",
  includes=["Never work on running equipment without proper isolation and LOTO"], star_tags=["safety"])
q("technical", "How would you validate that a report or dashboard's numbers are actually correct?", difficulty=M,
  assessing="Data validation discipline.",
  includes=["Cross-checking against a known source", "Spot-checking edge cases"])
q("technical", "What does 'mean time between failures' (MTBF) tell you about equipment reliability?", difficulty=M,
  concepts=["MTBF", "Reliability engineering"],
  assessing="Reliability metrics literacy.",
  includes=["Correct definition and how it's used to plan maintenance"])

# ---------------------------------------------------------------------------
# Safety (20+)
# ---------------------------------------------------------------------------

q("safety", "What would you do if you saw a coworker not following a safety procedure?", difficulty=M,
  assessing="Willingness to intervene on safety regardless of social discomfort.",
  includes=["Stop and address it immediately, respectfully", "Report per procedure if needed"], star_tags=["safety"])
q("safety", "Describe a time you identified a safety hazard. What did you do?", difficulty=M,
  assessing="Proactive hazard identification.",
  includes=["Specific hazard identified", "Immediate action taken", "How it was resolved/reported"], star_tags=["safety"])
q("safety", "Why is near-miss reporting important, even when no one was hurt?", difficulty=M,
  assessing="Understanding of proactive safety culture.",
  includes=["Near-misses reveal risk before an actual injury occurs"])
q("safety", "What would you do if you were asked to skip a safety step to save time?", difficulty=H,
  assessing="Willingness to prioritize safety over schedule pressure.",
  includes=["Refuse and explain why", "Escalate if pressured further"], star_tags=["safety", "decision_making"])
q("safety", "Describe your understanding of a Job Safety Analysis (JSA).", difficulty=M,
  concepts=["Hazard identification", "Task breakdown", "Control measures"],
  assessing="Familiarity with structured pre-task risk assessment.",
  includes=["Correct explanation of breaking a task into steps and identifying hazards per step"])
q("safety", "How do you stay alert to hazards during a repetitive task you've done hundreds of times?", difficulty=M,
  assessing="Awareness of complacency risk.",
  includes=["Acknowledges complacency risk", "A concrete habit to counter it"])
q("safety", "What personal protective equipment considerations matter most in your target role?", difficulty=E,
  assessing="Basic PPE awareness relevant to the role.",
  includes=["PPE relevant to the specific hazards of that role"])
q("safety", "Tell me about a time you had to respond to an emergency or urgent safety situation.", difficulty=H,
  assessing="Composure and correct action under real pressure.",
  includes=["Calm, procedure-based response", "Clear communication during the event"], star_tags=["safety", "pressure"])
q("safety", "How would you handle a situation where you're unsure if a task is safe to perform?", difficulty=M,
  assessing="Escalation instinct when uncertain.",
  includes=["Stop and ask rather than guessing"], star_tags=["safety", "decision_making"])
q("safety", "What does 'stop work authority' mean to you?", difficulty=M,
  assessing="Understanding that any employee can and should halt unsafe work.",
  includes=["Anyone can stop work regardless of position", "No penalty for using it in good faith"])
q("safety", "Describe how you would handle a spill of a hazardous material.", difficulty=H,
  assessing="Emergency response knowledge.",
  includes=["Follow the site's spill response procedure", "Prioritize personal and coworker safety first"], star_tags=["safety", "pressure"])
q("safety", "Why is proper communication during shift handover important for safety?", difficulty=M,
  assessing="Understanding of handover as a safety-critical process.",
  includes=["Prevents information loss about ongoing hazards/abnormal conditions"])
q("safety", "What would you do if equipment appeared to be malfunctioning but was still technically operable?", difficulty=H,
  assessing="Risk-averse judgment.",
  includes=["Report and have it inspected rather than continuing to run it"], star_tags=["safety", "equipment_failure"])
q("safety", "How do you balance production goals with safety requirements?", difficulty=H,
  assessing="Ensures safety is never compromised for output.",
  includes=["Safety takes priority even when it affects production targets"])
q("safety", "What steps would you take immediately after witnessing a workplace injury?", difficulty=H,
  assessing="Correct emergency response sequencing.",
  includes=["Ensure the area is safe, get help, follow first-aid/emergency procedure, report"], star_tags=["safety", "pressure"])
q("safety", "How do you ensure you understand a new safety procedure before performing a task?", difficulty=E,
  assessing="Diligence in following updated procedures.",
  includes=["Ask questions until fully clear before proceeding"])
q("safety", "What's your understanding of the hierarchy of hazard controls?", difficulty=H,
  concepts=["Elimination", "Substitution", "Engineering controls", "Administrative controls", "PPE"],
  assessing="Structured safety-engineering knowledge.",
  includes=["Correct order from most to least effective"])
q("safety", "Describe a time you had to remind someone senior to you about a safety rule.", difficulty=H,
  assessing="Confidence to enforce safety regardless of hierarchy.",
  includes=["Respectful but firm communication", "Follow-through"], star_tags=["safety", "leadership"])
q("safety", "What would you do if you noticed a safety sign or barrier was missing or damaged?", difficulty=E,
  assessing="Attentiveness to environmental safety controls.",
  includes=["Report it immediately and treat the area as hazardous until resolved"])
q("safety", "How would you explain the importance of safety to a new team member on their first day?", difficulty=M,
  assessing="Ability to model and communicate a safety-first culture.",
  includes=["Frames safety as a shared, non-negotiable responsibility"], star_tags=["safety", "communication"])

# ---------------------------------------------------------------------------
# Leadership (20+)
# ---------------------------------------------------------------------------

q("leadership", "Describe your leadership style.", difficulty=M,
  assessing="Self-awareness of leadership approach and its fit for the team.",
  includes=["A specific, coherent style", "An example demonstrating it"], star_tags=["leadership"])
q("leadership", "Tell me about a time you led a team through a difficult situation.", difficulty=H,
  assessing="Leadership under adversity.",
  includes=["The challenge", "How the team was guided/supported", "The outcome"], star_tags=["leadership", "pressure"])
q("leadership", "How do you motivate a team member who seems disengaged?", difficulty=M,
  assessing="People-management sensitivity.",
  includes=["Understanding the root cause first", "A tailored approach, not a generic fix"], star_tags=["leadership"])
q("leadership", "Describe a time you had to lead without formal authority.", difficulty=H,
  assessing="Influence-based leadership.",
  includes=["How credibility/buy-in was built without positional power"], star_tags=["leadership", "communication"])
q("leadership", "How do you delegate tasks effectively?", difficulty=M,
  assessing="Delegation judgment and trust-building.",
  includes=["Matching tasks to strengths", "Clear expectations and follow-up"], star_tags=["leadership"])
q("leadership", "Tell me about a time you had to make an unpopular decision.", difficulty=H,
  assessing="Willingness to make hard calls.",
  includes=["The reasoning behind the decision", "How it was communicated", "The outcome"], star_tags=["leadership", "decision_making"])
q("leadership", "How do you handle underperformance on your team?", difficulty=H,
  assessing="Constructive performance management.",
  includes=["Clear, direct, supportive conversation", "A concrete improvement plan"], star_tags=["leadership"])
q("leadership", "Describe how you build trust with a new team.", difficulty=M,
  assessing="Trust-building approach.",
  includes=["Consistency, transparency, and follow-through"], star_tags=["leadership", "teamwork"])
q("leadership", "Tell me about a time you had to give constructive criticism to someone who reacted poorly.", difficulty=H,
  assessing="Resilience and skill in difficult conversations.",
  includes=["Stayed calm and professional", "Focused on behavior, not personality"], star_tags=["leadership", "conflict"])
q("leadership", "How do you handle conflicting priorities from different stakeholders?", difficulty=H,
  assessing="Stakeholder management and prioritization under leadership.",
  includes=["A clear method for weighing and communicating tradeoffs"], star_tags=["leadership", "decision_making"])
q("leadership", "Describe a time you developed someone into a stronger performer.", difficulty=M,
  assessing="Coaching and development ability.",
  includes=["Specific coaching actions", "The measurable improvement"], star_tags=["leadership", "achievement"])
q("leadership", "How do you set expectations with a new team member?", difficulty=E,
  assessing="Clarity in expectation-setting.",
  includes=["Specific, measurable expectations communicated early"])
q("leadership", "Tell me about a time you had to rally a team around a shared goal.", difficulty=M,
  assessing="Vision communication and alignment.",
  includes=["How the goal was communicated", "How buy-in was achieved"], star_tags=["leadership", "communication"])
q("leadership", "How do you handle disagreement within your team?", difficulty=M,
  assessing="Facilitation of healthy conflict.",
  includes=["Creating space for open discussion", "Driving toward resolution"], star_tags=["leadership", "conflict"])
q("leadership", "Describe a time you had to lead a team with limited resources.", difficulty=H,
  assessing="Resourceful leadership under constraint.",
  includes=["Creative prioritization", "How morale was maintained"], star_tags=["leadership", "pressure"])
q("leadership", "How do you ensure accountability on your team without micromanaging?", difficulty=H,
  assessing="Balance of trust and oversight.",
  includes=["Clear ownership and checkpoints, not constant oversight"], star_tags=["leadership"])
q("leadership", "Tell me about a time you had to change your leadership approach for a specific person or situation.", difficulty=H,
  assessing="Situational leadership adaptability.",
  includes=["Recognized the need to adapt", "The adjusted approach and its result"], star_tags=["leadership"])
q("leadership", "How do you handle a situation where a team member disagrees with your decision?", difficulty=M,
  assessing="Openness to challenge while maintaining direction.",
  includes=["Listens genuinely", "Explains reasoning or adjusts if warranted"], star_tags=["leadership", "conflict"])
q("leadership", "Describe your approach to giving recognition to your team.", difficulty=E,
  assessing="Team morale and recognition practices.",
  includes=["Specific, timely, genuine recognition"])
q("leadership", "Tell me about a time you had to lead through organizational change.", difficulty=H,
  assessing="Change management leadership.",
  includes=["How uncertainty was addressed for the team", "How the transition was supported"], star_tags=["leadership", "pressure"])

# ---------------------------------------------------------------------------
# Management (20+)
# ---------------------------------------------------------------------------

q("management", "How do you approach setting goals for your team?", difficulty=M,
  assessing="Goal-setting methodology.",
  includes=["Specific, measurable goals aligned to broader objectives"])
q("management", "How do you conduct a performance review?", difficulty=M,
  assessing="Structured, fair performance evaluation.",
  includes=["Uses concrete evidence, not just impressions", "Two-way conversation"])
q("management", "Describe how you manage your own time as a manager.", difficulty=M,
  assessing="Personal time-management as a manager.",
  includes=["A concrete prioritization system"])
q("management", "How do you handle a direct report who consistently misses deadlines?", difficulty=H,
  assessing="Performance management approach.",
  includes=["Diagnose the root cause first", "A clear, supportive improvement plan"], star_tags=["leadership"])
q("management", "How do you decide what to delegate versus handle yourself?", difficulty=M,
  assessing="Delegation judgment.",
  includes=["Criteria based on development opportunity, urgency, and risk"])
q("management", "Describe your approach to running effective team meetings.", difficulty=E,
  assessing="Meeting facilitation skill.",
  includes=["Clear agenda", "Time-boxing", "Actionable outcomes"])
q("management", "How do you manage a team member who is more experienced than you?", difficulty=H,
  assessing="Managing upward-skill dynamics with humility and clarity.",
  includes=["Leverages their expertise", "Still provides clear direction where needed"], star_tags=["leadership"])
q("management", "How do you handle budget or resource constraints affecting your team?", difficulty=H,
  assessing="Resource-management judgment.",
  includes=["Transparent prioritization", "Creative problem-solving with what's available"], star_tags=["decision_making"])
q("management", "Describe how you onboard a new hire onto your team.", difficulty=M,
  assessing="Structured onboarding approach.",
  includes=["A clear plan covering expectations, training, and early check-ins"])
q("management", "How do you handle a disagreement between two of your direct reports?", difficulty=H,
  assessing="Conflict mediation as a manager.",
  includes=["Hears both sides fairly", "Drives toward a fair resolution"], star_tags=["conflict", "leadership"])
q("management", "How do you track progress toward team goals?", difficulty=M,
  assessing="Progress-tracking discipline.",
  includes=["Concrete metrics or checkpoints, not just gut feel"])
q("management", "Describe your approach to succession planning or backup coverage on your team.", difficulty=H,
  assessing="Long-term team resilience planning.",
  includes=["Cross-training or documented processes to reduce single points of failure"])
q("management", "How do you communicate difficult organizational decisions to your team?", difficulty=H,
  assessing="Transparent, empathetic communication under pressure.",
  includes=["Honesty balanced with empathy", "Space for questions"], star_tags=["leadership", "communication"])
q("management", "How do you decide when to escalate a team issue to your own manager?", difficulty=M,
  assessing="Judgment about scope of authority.",
  includes=["Clear criteria for what warrants escalation"], star_tags=["decision_making"])
q("management", "Describe how you balance being approachable with maintaining authority.", difficulty=H,
  assessing="Management presence and boundary-setting.",
  includes=["Concrete example of maintaining both"])
q("management", "How do you handle managing a remote or hybrid team?", difficulty=M,
  assessing="Remote-management practices.",
  includes=["Deliberate communication cadence and trust-building practices"])
q("management", "Describe a time you had to manage a project with a tight budget.", difficulty=H,
  assessing="Financial stewardship as a manager.",
  includes=["Prioritization decisions made", "The outcome"], star_tags=["decision_making", "achievement"])
q("management", "How do you ensure your team stays aligned with broader company priorities?", difficulty=M,
  assessing="Alignment and communication cascade.",
  includes=["Regular translation of company goals into team-level priorities"])
q("management", "How do you handle a situation where you inherited a team with low morale?", difficulty=H,
  assessing="Turnaround leadership.",
  includes=["Diagnosing root causes", "Concrete steps to rebuild morale"], star_tags=["leadership", "pressure"])
q("management", "Describe how you give feedback to a high performer versus a struggling performer.", difficulty=H,
  assessing="Tailored feedback approach.",
  includes=["Recognizes that feedback style should adapt to the individual"])

# ---------------------------------------------------------------------------
# Situational (20+)
# ---------------------------------------------------------------------------

q("situational", "What would you do if you were given a task with unclear instructions?", difficulty=E,
  assessing="Initiative in clarifying ambiguity.",
  includes=["Ask clarifying questions before proceeding"])
q("situational", "How would you handle discovering a mistake in a report right before it's due to be sent?", difficulty=M,
  assessing="Integrity and urgency under time pressure.",
  includes=["Fix it and flag the delay rather than sending it knowingly wrong"], star_tags=["decision_making", "pressure"])
q("situational", "What would you do if a customer or client was extremely upset with your company?", difficulty=M,
  assessing="Customer de-escalation approach.",
  includes=["Listen and acknowledge before problem-solving"], star_tags=["customer"])
q("situational", "How would you handle being assigned two urgent tasks with the same deadline?", difficulty=M,
  assessing="Prioritization and communication under conflicting demands.",
  includes=["Communicate the conflict and seek prioritization guidance if needed"])
q("situational", "What would you do if you noticed a colleague taking credit for your work?", difficulty=H,
  assessing="Assertiveness balanced with professionalism.",
  includes=["Address it directly and privately first"], star_tags=["conflict"])
q("situational", "How would you respond if your manager asked you to do something you believed was unethical?", difficulty=X,
  assessing="Ethical judgment under authority pressure.",
  includes=["Respectfully raise the concern", "Escalate further if necessary", "Refuse if truly unethical"], star_tags=["decision_making"])
q("situational", "What would you do if you were the only one who noticed a critical error before a major deadline?", difficulty=H,
  assessing="Ownership and communication under pressure.",
  includes=["Raise it immediately regardless of how it affects the timeline"], star_tags=["decision_making", "pressure"])
q("situational", "How would you handle joining a team where everyone already has established workflows you disagree with?", difficulty=H,
  assessing="Tact when introducing change as a newcomer.",
  includes=["Observe and build credibility before proposing changes"])
q("situational", "What would you do if you were unsure whether a task fell within your responsibilities?", difficulty=E,
  assessing="Clarity-seeking versus assuming.",
  includes=["Ask rather than assume or avoid the task"])
q("situational", "How would you handle a situation where you were asked to work with outdated or incomplete data?", difficulty=M,
  assessing="Data-quality judgment.",
  includes=["Flag the limitation and proceed cautiously, or seek better data first"])
q("situational", "What would you do if a project you were leading started falling behind schedule?", difficulty=H,
  assessing="Proactive project-risk management.",
  includes=["Diagnose the cause early", "Communicate transparently and adjust the plan"], star_tags=["decision_making", "leadership"])
q("situational", "How would you handle receiving conflicting instructions from two different supervisors?", difficulty=H,
  assessing="Navigating organizational ambiguity.",
  includes=["Seek clarification/alignment between the two rather than guessing"], star_tags=["communication"])
q("situational", "What would you do if you made a commitment to a deadline you later realized was unrealistic?", difficulty=M,
  assessing="Early, honest communication of risk.",
  includes=["Flag it as early as possible with a revised plan"])
q("situational", "How would you handle a situation where a team member wasn't pulling their weight on a shared project?", difficulty=M,
  assessing="Peer accountability without escalation-first instinct.",
  includes=["Address it directly with the person before escalating"], star_tags=["teamwork", "conflict"])
q("situational", "What would you do if you disagreed with feedback given to you in a performance review?", difficulty=M,
  assessing="Professional handling of disagreement with formal feedback.",
  includes=["Ask for specific examples", "Respond professionally, not defensively"])
q("situational", "How would you handle being asked to train a new colleague while also managing your own full workload?", difficulty=M,
  assessing="Balancing competing responsibilities.",
  includes=["Communicate the tradeoff and negotiate time/priority if needed"])
q("situational", "What would you do if you spotted a safety or quality issue that wasn't part of your job to fix?", difficulty=M,
  assessing="Ownership beyond narrow job scope.",
  includes=["Report it regardless of whose job it technically is"], star_tags=["safety"])
q("situational", "How would you handle a situation where your team's goals conflicted with another team's goals?", difficulty=H,
  assessing="Cross-team negotiation and prioritization.",
  includes=["Seek alignment through discussion rather than unilateral action"])
q("situational", "What would you do if you were unexpectedly asked to present something you weren't fully prepared for?", difficulty=M,
  assessing="Composure and adaptability under pressure.",
  includes=["Stay calm, be transparent about preparation level, focus on what is known"], star_tags=["pressure"])
q("situational", "How would you handle discovering that a long-standing process at your company was actually incorrect or outdated?", difficulty=H,
  assessing="Constructive challenge of the status quo.",
  includes=["Raise it constructively with evidence rather than criticizing past decisions"], star_tags=["process_improvement"])

# ---------------------------------------------------------------------------
# Career Motivation (15+)
# ---------------------------------------------------------------------------

q("career_motivation", "What made you choose this career path?", difficulty=E,
  assessing="Genuine, coherent career narrative.",
  includes=["A specific, believable origin story", "Connection to their current direction"])
q("career_motivation", "Why are you interested in this industry?", difficulty=E,
  assessing="Authentic industry interest versus a generic answer.",
  includes=["A specific reason tied to the industry's realities"])
q("career_motivation", "What are your long-term career goals?", difficulty=M,
  assessing="Clarity and realism of long-term direction.",
  includes=["A coherent goal consistent with this role being a step toward it"])
q("career_motivation", "What would make you leave a job?", difficulty=M,
  assessing="Values and red flags for retention risk.",
  includes=["Reasonable, professional criteria"])
q("career_motivation", "How does this role fit into your career plan?", difficulty=M,
  assessing="Whether the role is a genuine fit, not just any job.",
  includes=["A clear, specific connection between the role and their trajectory"])
q("career_motivation", "What type of work makes you feel most fulfilled?", difficulty=E,
  assessing="Self-awareness of intrinsic motivators.",
  includes=["A specific type of work with a reason why"])
q("career_motivation", "What skills are you hoping to develop in your next role?", difficulty=E,
  assessing="Growth orientation aligned with the role's realities.",
  includes=["Skills genuinely available to develop in this role"])
q("career_motivation", "Why did you choose to apply to this company specifically?", difficulty=M,
  assessing="Genuine company interest versus a mass application.",
  includes=["A specific, researched reason"])
q("career_motivation", "What does career success look like to you?", difficulty=M,
  assessing="Personal definition of success and its realism.",
  includes=["A specific, personally meaningful definition"])
q("career_motivation", "How do you decide which opportunities to pursue?", difficulty=M,
  assessing="Decision criteria for career moves.",
  includes=["Clear, consistent criteria"])
q("career_motivation", "What's the biggest factor that would make you accept a job offer?", difficulty=M,
  assessing="Priorities in decision-making, useful for negotiation context.",
  includes=["A genuine, well-reasoned priority"])
q("career_motivation", "How has your career path prepared you for this specific role?", difficulty=M,
  assessing="Ability to connect past experience directly to the target role.",
  includes=["Specific, relevant experience mapped to the role's requirements"])
q("career_motivation", "What would you want to accomplish in your first 90 days in this role?", difficulty=M,
  assessing="Preparedness and realistic early-role planning.",
  includes=["Concrete, achievable early goals"])
q("career_motivation", "Why do you think you're ready for this next step in your career?", difficulty=M,
  assessing="Self-assessment of readiness with evidence.",
  includes=["Specific evidence of readiness, not just confidence alone"])
q("career_motivation", "What's something about your career you would do differently if you could?", difficulty=H,
  assessing="Honest reflection without excessive regret framing.",
  includes=["An honest, non-defensive reflection with a lesson learned"])

# ---------------------------------------------------------------------------
# Company-Specific / Job-Specific (generic, company_id=None — editorial category tagging only)
# ---------------------------------------------------------------------------

q("company_specific", "Why do you want to work for this company specifically, rather than a competitor?", difficulty=M,
  assessing="Depth of company research and genuine interest.",
  includes=["Specific, researched reasons unique to this company"])
q("company_specific", "What do you think are the biggest opportunities or challenges facing this company right now?", difficulty=H,
  assessing="Business awareness and critical thinking about the employer.",
  includes=["An informed, balanced perspective based on public information"])
q("company_specific", "How do you see yourself contributing to this company's mission?", difficulty=M,
  assessing="Alignment between personal contribution and company mission.",
  includes=["A specific, credible connection"])
q("company_specific", "What do you know about our company's recent developments or news?", difficulty=M,
  assessing="Whether the candidate did up-to-date research.",
  includes=["A specific, accurate, recent fact"])
q("company_specific", "What about our company culture appeals to you?", difficulty=E,
  assessing="Cultural fit and genuine interest.",
  includes=["A specific cultural element, not a generic platitude"])
q("company_specific", "How would you describe our company to someone who has never heard of it?", difficulty=M,
  assessing="Understanding of the company's core business and positioning.",
  includes=["An accurate, concise description"])
q("company_specific", "What sets this company apart from others in the industry, in your view?", difficulty=H,
  assessing="Competitive/market awareness.",
  includes=["A specific, defensible differentiator"])
q("company_specific", "Have you used our products or services? What did you think?", difficulty=E,
  assessing="Genuine familiarity with the company's output.",
  includes=["Honest, specific feedback if they have experience, or honest acknowledgment if not"])
q("company_specific", "What questions do you have about our company that weren't answered by your research?", difficulty=M,
  assessing="Depth of preparation and genuine curiosity.",
  includes=["Specific, non-generic questions"])
q("company_specific", "Why now? Why are you looking to join this company at this point in your career?", difficulty=M,
  assessing="Timing and motivation clarity.",
  includes=["A coherent link between career timing and this opportunity"])

q("job_specific", "What part of this role's day-to-day responsibilities excites you the most?", difficulty=E,
  assessing="Genuine interest in the actual job content.",
  includes=["A specific responsibility from the job posting, not a vague answer"])
q("job_specific", "Which of the requirements listed for this role do you feel strongest in, and which would need development?", difficulty=M,
  assessing="Honest self-assessment against the actual job requirements.",
  includes=["Specific requirement matched to real experience", "Honest acknowledgment of a development area"])
q("job_specific", "How does your experience align with the core responsibilities of this position?", difficulty=M,
  assessing="Ability to map past experience onto this specific role.",
  includes=["Direct mapping of past experience to listed responsibilities"])
q("job_specific", "What would your first month look like if you were hired for this role?", difficulty=M,
  assessing="Realistic planning specific to this role.",
  includes=["Concrete, role-appropriate early actions"])
q("job_specific", "What do you think is the most important skill for succeeding in this specific role?", difficulty=M,
  assessing="Understanding of what actually drives success in this position.",
  includes=["A skill genuinely central to the role, with reasoning"])
q("job_specific", "How would you handle the specific challenges mentioned in this job's description?", difficulty=H,
  assessing="Preparedness for the role's stated challenges.",
  includes=["A specific approach tied to a challenge named in the posting"])
q("job_specific", "This role requires working closely with [a specific function]. How have you worked with that function before?", difficulty=M,
  assessing="Relevant cross-functional experience for this specific role.",
  includes=["A concrete past example of working with that function"])
q("job_specific", "What tools or systems mentioned in this job posting are you already familiar with?", difficulty=E,
  assessing="Technical readiness for the specific tools this role uses.",
  includes=["Honest, specific familiarity level with named tools"])
q("job_specific", "How would you prioritize the responsibilities listed in this job description in your first few weeks?", difficulty=M,
  assessing="Practical prioritization specific to this role's scope.",
  includes=["A reasonable, role-appropriate prioritization"])
q("job_specific", "What questions do you have about the day-to-day expectations of this specific role?", difficulty=E,
  assessing="Genuine engagement with the role's realities.",
  includes=["Specific, role-relevant questions"])


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(InterviewQuestion).where(InterviewQuestion.is_demo.is_(True)))).scalars().first()
        if existing is not None:
            print("Demo interview questions already present — skipping seed.")
            return

        categories_by_slug: dict[str, InterviewQuestionCategory] = {}
        for data in CATEGORIES:
            category = InterviewQuestionCategory(**data)
            db.add(category)
            await db.flush()
            categories_by_slug[data["slug"]] = category
            print(f"Created interview category: {category.name}")

        topics_by_slug: dict[str, InterviewTopic] = {}
        for category_slug, name, slug, field, industry in TOPICS:
            topic = InterviewTopic(
                category_id=categories_by_slug[category_slug].id, name=name, slug=slug, field=field, industry=industry
            )
            db.add(topic)
            await db.flush()
            topics_by_slug[slug] = topic
        print(f"Created {len(topics_by_slug)} interview topics.")

        created = 0
        for entry in QUESTIONS:
            topic = topics_by_slug[entry["topic"]] if entry["topic"] else None
            question = InterviewQuestion(
                question_text=entry["question_text"],
                category_id=categories_by_slug[entry["category"]].id,
                topic_id=topic.id if topic else None,
                field=topic.field if topic else None,
                industry=topic.industry if topic else None,
                experience_level=entry["experience_level"],
                difficulty=entry["difficulty"],
                answer_guidance=entry["answer_guidance"],
                evaluation_points=entry["evaluation_points"],
                follow_up_prompt=entry["follow_up_prompt"],
                star_tags=entry["star_tags"],
                is_active=True,
                is_demo=True,
            )
            db.add(question)
            created += 1

        await db.commit()
        print(f"Seeded {created} demo interview questions across {len(categories_by_slug)} categories.")


if __name__ == "__main__":
    asyncio.run(seed())
