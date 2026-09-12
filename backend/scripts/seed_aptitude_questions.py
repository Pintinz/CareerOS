"""Seeds the aptitude question bank for local development (Phase 6 spec §4/§12-16/§35).

Every question here is fictional-but-correct practice content, flagged `is_demo=True` like every
other seeded record in this project. Real answers, real explanations — this is not placeholder
text. Abstract-reasoning questions are represented with emoji/text shape sequences rather than
real images: no image storage/rendering pipeline exists yet for the question bank, so this is a
documented simplification (see PROJECT_STATUS.md), not a silent fake — `question_image_url` stays
null on every seeded question and the question text itself carries the visual pattern.

Safe to re-run: skips seeding if any demo question already exists.

Usage:
    cd backend && python -m scripts.seed_aptitude_questions
"""

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import admin_user, profile, user  # noqa: F401  (resolves cross-model FKs)
from app.models.question import Question, QuestionCategory, QuestionDifficulty, QuestionOption, QuestionTopic, QuestionType

# ---------------------------------------------------------------------------
# Categories (the six fixed sections, spec §4)
# ---------------------------------------------------------------------------

CATEGORIES = [
    dict(name="Numerical Reasoning", slug="numerical", description="Percentages, ratios, averages, data interpretation, and other quantitative reasoning."),
    dict(name="Verbal Reasoning", slug="verbal", description="Reading comprehension, inference, critical reasoning, and vocabulary."),
    dict(name="Abstract Reasoning", slug="abstract", description="Shape sequences, rotation, pattern recognition, and spatial reasoning."),
    dict(name="Logical Reasoning", slug="logical", description="Syllogisms, deduction, series completion, and seating/coding puzzles."),
    dict(name="Situational Judgement", slug="situational-judgement", description="Workplace scenarios testing judgement, teamwork, and professionalism."),
    dict(name="Technical / Skill", slug="technical", description="Field-, industry-, and role-specific technical knowledge."),
]

# (category_slug, name, slug, field, industry)
TOPICS = [
    ("numerical", "Percentages", "percentages", None, None),
    ("numerical", "Ratios", "ratios", None, None),
    ("numerical", "Fractions", "fractions", None, None),
    ("numerical", "Averages", "averages", None, None),
    ("numerical", "Charts, Tables and Graphs", "charts-tables-graphs", None, None),
    ("numerical", "Profit and Loss", "profit-and-loss", None, None),
    ("numerical", "Rates", "rates", None, None),
    ("numerical", "Speed, Distance and Time", "speed-distance-time", None, None),
    ("numerical", "Work Rate", "work-rate", None, None),
    ("numerical", "Statistics", "numerical-statistics", None, None),
    ("numerical", "Data Interpretation", "data-interpretation", None, None),
    ("numerical", "Sequences", "numerical-sequences", None, None),
    ("verbal", "Reading Comprehension", "reading-comprehension", None, None),
    ("verbal", "True/False/Cannot Say", "true-false-cannot-say", None, None),
    ("verbal", "Inference", "verbal-inference", None, None),
    ("verbal", "Critical Reasoning", "critical-reasoning", None, None),
    ("verbal", "Sentence Completion", "sentence-completion", None, None),
    ("verbal", "Vocabulary", "vocabulary", None, None),
    ("verbal", "Argument Analysis", "argument-analysis", None, None),
    ("abstract", "Shape Sequences", "shape-sequences", None, None),
    ("abstract", "Rotation", "rotation", None, None),
    ("abstract", "Matrices", "abstract-matrices", None, None),
    ("abstract", "Odd One Out", "odd-one-out", None, None),
    ("abstract", "Mirroring", "mirroring", None, None),
    ("abstract", "Pattern Progression", "pattern-progression", None, None),
    ("abstract", "Spatial Reasoning", "spatial-reasoning", None, None),
    ("logical", "Syllogisms", "syllogisms", None, None),
    ("logical", "Coding-Decoding", "coding-decoding", None, None),
    ("logical", "Blood Relations", "blood-relations", None, None),
    ("logical", "Series Completion", "logical-series-completion", None, None),
    ("logical", "Logical Deduction", "logical-deduction", None, None),
    ("logical", "Venn Diagrams", "venn-diagrams", None, None),
    ("logical", "Seating Arrangements", "seating-arrangements", None, None),
    ("situational-judgement", "Workplace Scenarios", "workplace-scenarios", None, None),
    ("situational-judgement", "Teamwork", "teamwork", None, None),
    ("situational-judgement", "Customer Service", "customer-service", None, None),
    ("situational-judgement", "Conflict Resolution", "conflict-resolution", None, None),
    ("situational-judgement", "Time Management", "time-management", None, None),
    ("situational-judgement", "Ethics and Integrity", "ethics-integrity", None, None),
    # Technical topics — slugs match app/aptitude/technical_topic_map.py exactly so job-specific
    # generation actually finds them.
    ("technical", "Pumps", "pumps", "Mechanical Engineering", "Oil & Gas"),
    ("technical", "Valves", "valves", "Mechanical Engineering", "Oil & Gas"),
    ("technical", "Compressors", "compressors", "Mechanical Engineering", "Oil & Gas"),
    ("technical", "P&IDs", "p-and-ids", "Process Operations", "Oil & Gas"),
    ("technical", "DCS", "dcs", "Process Operations", "Oil & Gas"),
    ("technical", "SCADA", "scada", "Electrical Engineering", "Oil & Gas"),
    ("technical", "Instrumentation", "instrumentation", "Electrical Engineering", "Oil & Gas"),
    ("technical", "Process Safety", "process-safety", "Process Operations", "Oil & Gas"),
    ("technical", "Flow", "flow", "Process Operations", "Oil & Gas"),
    ("technical", "Pressure", "pressure", "Process Operations", "Oil & Gas"),
    ("technical", "Temperature", "temperature", "Process Operations", "Oil & Gas"),
    ("technical", "Heat Exchangers", "heat-exchangers", "Mechanical Engineering", "Oil & Gas"),
    ("technical", "Separators", "separators", "Process Operations", "Oil & Gas"),
    ("technical", "LOTO", "loto", None, None),
    ("technical", "Troubleshooting", "troubleshooting", "Mechanical Engineering", None),
    ("technical", "Fluid Mechanics", "fluid-mechanics", "Mechanical Engineering", None),
    ("technical", "Thermodynamics", "thermodynamics", "Mechanical Engineering", None),
    ("technical", "SQL", "sql", "Data Analysis", None),
    ("technical", "Excel / Spreadsheets", "excel", "Data Analysis", None),
    ("technical", "Statistics", "statistics", "Data Analysis", None),
    ("technical", "Data Interpretation", "technical-data-interpretation", "Data Analysis", None),
    ("technical", "Data Visualization", "visualization", "Data Analysis", None),
    ("technical", "Probability", "probability", "Data Analysis", None),
    ("technical", "Computer Literacy", "computer-literacy", None, None),
    ("technical", "MS Office", "ms-office", None, None),
    ("technical", "Email Etiquette", "email-etiquette", None, None),
    ("technical", "Cybersecurity Basics", "cybersecurity-basics", None, None),
    ("technical", "Project Management Basics", "project-management-basics", None, None),
]

E, M, H, X = (
    QuestionDifficulty.EASY,
    QuestionDifficulty.MEDIUM,
    QuestionDifficulty.HARD,
    QuestionDifficulty.EXPERT,
)

# Each question: (category_slug, topic_slug, difficulty, question_text, options, explanation)
# `options` is a list of (text, is_correct) tuples for choice questions, or None for numeric
# questions (which instead carry `numeric=(value, tolerance)` appended as a 6th element).
QUESTIONS: list[tuple] = []


def q(category, topic, difficulty, text, options, explanation, passage=None, qtype=QuestionType.SINGLE_CHOICE):
    QUESTIONS.append((category, topic, difficulty, qtype, text, options, explanation, passage, None))


def q_numeric(category, topic, difficulty, text, value, tolerance, explanation):
    QUESTIONS.append((category, topic, difficulty, QuestionType.NUMERIC, text, None, explanation, None, (value, tolerance)))


# ---------------------------------------------------------------------------
# Numerical (26)
# ---------------------------------------------------------------------------

q_numeric("numerical", "percentages", E, "What is 15% of 200? (Enter the numeric value.)", 30, 0, "15% of 200 = 0.15 x 200 = 30.")
q("numerical", "percentages", M, "A price increased from $80 to $100. What is the percentage increase?",
  [("25%", True), ("20%", False), ("15%", False), ("30%", False)],
  "Increase = $20. 20/80 = 25%.")
q("numerical", "ratios", E, "Simplify the ratio 12:16.",
  [("3:4", True), ("4:3", False), ("2:3", False), ("3:5", False)],
  "Divide both sides by their greatest common factor, 4: 12/4=3, 16/4=4.")
q("numerical", "ratios", M, "The ratio of boys to girls in a class is 3:5. If there are 24 boys, how many girls are there?",
  [("40", True), ("35", False), ("45", False), ("30", False)],
  "Each 'part' = 24/3 = 8. Girls = 5 x 8 = 40.")
q("numerical", "fractions", E, "What is 3/4 + 1/8?",
  [("7/8", True), ("1/2", False), ("5/8", False), ("1", False)],
  "Convert to a common denominator of 8: 6/8 + 1/8 = 7/8.")
q("numerical", "fractions", M, "Which of these fractions is the largest?",
  [("11/12", True), ("5/6", False), ("7/9", False), ("3/4", False)],
  "As decimals: 11/12=0.917, 5/6=0.833, 7/9=0.778, 3/4=0.75. 11/12 is largest.")
q("numerical", "averages", E, "Find the average of 12, 18, 24, and 30.",
  [("21", True), ("20", False), ("22", False), ("24", False)],
  "Sum = 84. 84 / 4 = 21.")
q("numerical", "averages", M, "The average of 5 numbers is 20. One number is removed and the average of the remaining 4 is 18. What was the removed number?",
  [("28", True), ("25", False), ("30", False), ("22", False)],
  "Original total = 5x20=100. Remaining total = 4x18=72. Removed number = 100-72=28.")
q("numerical", "averages", H, "The average weight of 8 people increases by 2.5 kg when a new person replaces one who weighs 65 kg. What is the weight of the new person?",
  [("85 kg", True), ("80 kg", False), ("75 kg", False), ("90 kg", False)],
  "Total weight increase = 8 x 2.5 = 20 kg. New person's weight = 65 + 20 = 85 kg.")
q("numerical", "charts-tables-graphs", M, "A survey of 200 people found 40% prefer tea, 35% prefer coffee, and the rest prefer juice. How many people prefer juice?",
  [("50", True), ("40", False), ("60", False), ("45", False)],
  "Juice share = 100% - 40% - 35% = 25%. 25% of 200 = 50.")
q("numerical", "profit-and-loss", E, "A shopkeeper buys an item for $50 and sells it for $65. What is the profit percentage?",
  [("30%", True), ("25%", False), ("15%", False), ("35%", False)],
  "Profit = $15. 15/50 = 30%.")
q("numerical", "profit-and-loss", M, "An item is sold at a loss of 20% for $160. What was the cost price?",
  [("$200", True), ("$180", False), ("$192", False), ("$220", False)],
  "CP x 0.8 = 160, so CP = 160 / 0.8 = $200.")
q("numerical", "rates", E, "If 5 workers can complete a task in 10 days, how many days will 10 workers take, assuming a constant work rate per worker?",
  [("5 days", True), ("10 days", False), ("8 days", False), ("12 days", False)],
  "Work is inversely proportional to the number of workers: (5 x 10) / 10 = 5 days.")
q_numeric("numerical", "speed-distance-time", E, "A car travels 180 km in 3 hours. What is its average speed in km/h? (Enter the numeric value.)", 60, 0, "Speed = distance / time = 180 / 3 = 60 km/h.")
q("numerical", "speed-distance-time", M, "Two trains start from stations 300 km apart and move towards each other at 60 km/h and 90 km/h. After how many hours will they meet?",
  [("2 hours", True), ("2.5 hours", False), ("3 hours", False), ("1.5 hours", False)],
  "Combined closing speed = 150 km/h. Time = 300 / 150 = 2 hours.")
q("numerical", "work-rate", E, "If a pump can fill a tank in 4 hours, what fraction of the tank does it fill in 1 hour?",
  [("1/4", True), ("1/2", False), ("1/3", False), ("1/5", False)],
  "The pump fills 1/4 of the tank per hour, by definition of its rate.")
q("numerical", "work-rate", M, "A can complete a job in 6 days, B in 12 days. Working together, how many days will they take?",
  [("4 days", True), ("3 days", False), ("5 days", False), ("6 days", False)],
  "Combined rate = 1/6 + 1/12 = 3/12 = 1/4 of the job per day, so the job takes 4 days.")
q("numerical", "work-rate", H, "A can do a job in 8 days and B in 10 days. They work together for 2 days, then A leaves. How many more days does B need to finish?",
  [("5.5 days", True), ("5 days", False), ("6 days", False), ("4.5 days", False)],
  "Combined rate = 1/8+1/10 = 9/40 per day. In 2 days: 18/40 done. Remaining 22/40 = 11/20. B alone needs (11/20)/(1/10) = 5.5 days.")
q("numerical", "numerical-statistics", E, "What is the mode of this dataset: 2, 3, 3, 5, 7, 3, 9?",
  [("3", True), ("5", False), ("7", False), ("2", False)],
  "3 appears three times, more than any other value.")
q("numerical", "numerical-statistics", M, "What is the median of: 4, 8, 15, 16, 23, 42?",
  [("15.5", True), ("15", False), ("16", False), ("19", False)],
  "With 6 values, the median is the average of the 3rd and 4th: (15+16)/2 = 15.5.")
q("numerical", "data-interpretation", M, "Department A has 40 employees earning an average of $50,000; Department B has 60 employees earning an average of $60,000. What is the overall average salary?",
  [("$56,000", True), ("$55,000", False), ("$58,000", False), ("$54,000", False)],
  "Weighted average = (40x50,000 + 60x60,000) / 100 = (2,000,000+3,600,000)/100 = $56,000.")
q("numerical", "numerical-sequences", E, "Find the next number: 2, 4, 8, 16, ?",
  [("32", True), ("24", False), ("30", False), ("36", False)],
  "Each term doubles the previous one: 16 x 2 = 32.")
q("numerical", "numerical-sequences", M, "Find the next number: 1, 1, 2, 3, 5, 8, ?",
  [("13", True), ("11", False), ("14", False), ("12", False)],
  "This is the Fibonacci sequence: each term is the sum of the two before it. 5+8=13.")
q("numerical", "numerical-sequences", H, "Find the next number: 3, 7, 15, 31, ?",
  [("63", True), ("59", False), ("61", False), ("67", False)],
  "Each term follows the pattern (previous x 2) + 1: 31 x 2 + 1 = 63.")
q("numerical", "percentages", H, "A number is increased by 20% and then decreased by 20%. What is the net percentage change?",
  [("A 4% decrease", True), ("No change", False), ("A 2% decrease", False), ("A 4% increase", False)],
  "1.2 x 0.8 = 0.96, which is a 4% net decrease from the original value.")
q("numerical", "ratios", H, "A sum of $600 is divided among A, B, and C in the ratio 2:3:5. How much does C get?",
  [("$300", True), ("$200", False), ("$250", False), ("$350", False)],
  "Total parts = 10, so each part = $60. C gets 5 x $60 = $300.")

# ---------------------------------------------------------------------------
# Verbal (26)
# ---------------------------------------------------------------------------

RENEWABLE_PASSAGE = (
    "Renewable energy sources such as solar and wind power have grown rapidly over the past decade. "
    "While upfront installation costs remain higher than fossil fuel plants, operating costs are "
    "significantly lower over the plant's lifetime. Governments in several countries have introduced "
    "subsidies to accelerate adoption, though critics argue that intermittent supply still requires "
    "backup from conventional sources."
)
q("verbal", "reading-comprehension", E, "According to the passage, renewable energy plants generally have:",
  [("Higher upfront costs but lower long-term operating costs", True), ("Lower upfront and lower operating costs", False),
   ("Higher costs throughout their lifetime", False), ("The same costs as fossil fuel plants", False)],
  "The passage states upfront costs are higher but operating costs are lower over the plant's lifetime.",
  passage=RENEWABLE_PASSAGE, qtype=QuestionType.PASSAGE_BASED)
q("verbal", "true-false-cannot-say", M, "Based on the passage: 'Critics of renewable energy argue that intermittent supply requires backup from conventional sources.'",
  [("True", True), ("False", False), ("Cannot Say", False)],
  "This is stated directly in the passage's final sentence.",
  passage=RENEWABLE_PASSAGE, qtype=QuestionType.PASSAGE_BASED)
q("verbal", "reading-comprehension", M, "The passage suggests that government subsidies exist because:",
  [("Unaided adoption of renewables would likely be slower", True), ("Renewables are more expensive to operate", False),
   ("Fossil fuels are being banned", False), ("Solar power is unreliable", False)],
  "Subsidies are described as a way to 'accelerate adoption', implying adoption would otherwise be slower.",
  passage=RENEWABLE_PASSAGE, qtype=QuestionType.PASSAGE_BASED)
q("verbal", "verbal-inference", H, "Which of the following can be inferred from the passage?",
  [("Without subsidies, renewable adoption would likely still proceed but at a slower pace", True),
   ("Fossil fuel plants will soon be obsolete", False), ("Wind power is more reliable than solar", False),
   ("Subsidies have eliminated the need for backup power", False)],
  "The passage never claims renewables would stop growing without subsidies, only that subsidies accelerate the trend — the reasonable inference is a slower, not absent, pace.",
  passage=RENEWABLE_PASSAGE, qtype=QuestionType.PASSAGE_BASED)

TIME_MGMT_PASSAGE = (
    "Effective time management is not simply about doing more in less time — it is about prioritizing "
    "tasks according to their importance rather than their urgency. Many people fall into the trap of "
    "responding to whatever demands attention first, which often means urgent but low-value tasks crowd "
    "out important, high-value work. A widely used technique to counter this is dividing tasks into four "
    "categories based on urgency and importance."
)
q("verbal", "reading-comprehension", E, "According to the passage, effective time management primarily requires prioritizing by:",
  [("Importance rather than urgency", True), ("Urgency rather than importance", False),
   ("Speed of completion", False), ("Personal preference", False)],
  "The passage opens by stating time management is about prioritizing by importance, not urgency.",
  passage=TIME_MGMT_PASSAGE, qtype=QuestionType.PASSAGE_BASED)
q("verbal", "true-false-cannot-say", M, "Based on the passage: 'Urgent tasks are always more important than non-urgent tasks.'",
  [("True", False), ("False", True), ("Cannot Say", False)],
  "The passage explicitly warns that urgent but low-value tasks can crowd out important work — the opposite of this statement.",
  passage=TIME_MGMT_PASSAGE, qtype=QuestionType.PASSAGE_BASED)
q("verbal", "reading-comprehension", M, "The 'trap' described in the passage refers to:",
  [("Responding to whatever seems urgent instead of what matters most", True), ("Not doing enough work", False),
   ("Avoiding all urgent tasks", False), ("Delegating too much work", False)],
  "The passage describes the trap as responding to whatever demands attention first rather than what is most important.",
  passage=TIME_MGMT_PASSAGE, qtype=QuestionType.PASSAGE_BASED)

q("verbal", "true-false-cannot-say", M, "Statement: All engineers in the company have completed a safety certification. Tom works in the company as an engineer. Conclusion: Tom has completed a safety certification.",
  [("True", True), ("False", False), ("Cannot Say", False)],
  "If all engineers are certified and Tom is an engineer in the company, the conclusion follows logically.")
q("verbal", "true-false-cannot-say", M, "Statement: No cats are dogs. Some pets are cats. Conclusion: Some pets are not dogs.",
  [("True", True), ("False", False), ("Cannot Say", False)],
  "Since some pets are cats, and no cats are dogs, those pets that are cats are not dogs — the conclusion is valid.")
q("verbal", "critical-reasoning", M, "Argument: 'The company should reduce its workforce because sales have declined for two consecutive quarters.' Which of the following, if true, would most weaken this argument?",
  [("The decline in sales was due to a temporary supply shortage that has since been resolved", True),
   ("The company's competitors have also seen declining sales", False), ("Employee morale has been low recently", False),
   ("The company plans to launch a new product next year", False)],
  "If the cause of the decline was temporary and already resolved, the underlying rationale for cutting the workforce no longer holds.")
q("verbal", "critical-reasoning", M, "A company claims its new product is popular because online reviews are overwhelmingly positive. What is a weakness of this evidence?",
  [("People who leave reviews may not represent the average customer", True), ("Reviews are always accurate", False),
   ("The product must be low quality", False), ("Online reviews are illegal", False)],
  "Review-writers are a self-selected sample and may not reflect the broader customer base.")
q("verbal", "sentence-completion", E, "Despite the heavy rain, the outdoor event proceeded as planned because the organizers had ______ a large tent.",
  [("erected", True), ("dismantled", False), ("ignored", False), ("postponed", False)],
  "'Erected' (put up) makes sense in context — the tent protected the event from the rain.")
q("verbal", "sentence-completion", M, "The new policy, which was intended to reduce costs, instead ______ expenses due to unforeseen implementation challenges.",
  [("increased", True), ("decreased", False), ("stabilized", False), ("eliminated", False)],
  "The word 'instead' signals a contrast with the intended outcome (reducing costs), so expenses must have gone up.")
q("verbal", "sentence-completion", M, "The manager was so ______ about the project's success that she assured the board it would launch on time.",
  [("confident", True), ("doubtful", False), ("indifferent", False), ("hesitant", False)],
  "Assuring the board of on-time success implies confidence, not doubt or hesitation.")
q("verbal", "sentence-completion", H, "The auditor's report was ______ in its criticism, leaving no ambiguity about the company's financial mismanagement.",
  [("unequivocal", True), ("vague", False), ("flattering", False), ("neutral", False)],
  "'Leaving no ambiguity' matches 'unequivocal', meaning clear and unambiguous.")
q("verbal", "vocabulary", E, "Choose the word most similar in meaning to 'meticulous'.",
  [("careful and precise", True), ("careless", False), ("fast", False), ("lazy", False)],
  "'Meticulous' means showing great attention to detail; careful and precise.")
q("verbal", "vocabulary", E, "Choose the word most similar in meaning to 'concise'.",
  [("brief", True), ("lengthy", False), ("vague", False), ("complicated", False)],
  "'Concise' means giving information clearly in few words, i.e. brief.")
q("verbal", "vocabulary", M, "Choose the word most nearly OPPOSITE in meaning to 'transparent' (describing an organization's practices).",
  [("secretive", True), ("honest", False), ("open", False), ("clear", False)],
  "'Transparent' practices are open and clear; the opposite is 'secretive'.")
q("verbal", "vocabulary", M, "Choose the word most similar in meaning to 'ambiguous'.",
  [("unclear", True), ("obvious", False), ("certain", False), ("simple", False)],
  "'Ambiguous' means open to more than one interpretation, i.e. unclear.")
q("verbal", "vocabulary", M, "Choose the word most similar in meaning to 'pragmatic'.",
  [("practical", True), ("theoretical", False), ("emotional", False), ("idealistic", False)],
  "'Pragmatic' means dealing with things sensibly and realistically, i.e. practical.")
q("verbal", "vocabulary", H, "Choose the word most nearly OPPOSITE in meaning to 'reticent'.",
  [("talkative", True), ("quiet", False), ("shy", False), ("reserved", False)],
  "'Reticent' means reluctant to speak; the opposite is 'talkative'.")
q("verbal", "argument-analysis", H, "Argument: 'Since the introduction of the new software, productivity has increased by 15%. Therefore, the software caused the productivity increase.' What is the main flaw in this reasoning?",
  [("It assumes causation from correlation without ruling out other factors", True), ("It uses too large a sample size", False),
   ("It doesn't define productivity", False), ("It contradicts itself", False)],
  "The argument assumes the software caused the change without ruling out other explanations occurring at the same time.")
q("verbal", "argument-analysis", M, "Which of the following best describes a 'straw man' argument?",
  [("Misrepresenting an opponent's position to make it easier to attack", True), ("Presenting strong evidence for a claim", False),
   ("Agreeing with an opponent's position", False), ("Citing an expert's opinion", False)],
  "A straw man fallacy involves distorting an opposing argument to make it easier to refute.")
q("verbal", "critical-reasoning", E, "Which of the following is an assumption underlying the statement: 'We should hire more staff because customer complaints have increased'?",
  [("More staff would reduce customer complaints", True), ("Customer complaints are unimportant", False),
   ("The company has enough budget", False), ("Staff are currently underpaid", False)],
  "The argument only makes sense if hiring more staff is assumed to address the cause of the complaints.")
q("verbal", "verbal-inference", E, "If it is true that 'all managers attended the meeting' and 'Sarah did not attend the meeting', what can be concluded?",
  [("Sarah is not a manager", True), ("Sarah is a manager", False), ("The meeting was cancelled", False), ("Cannot be determined", False)],
  "If all managers attended and Sarah didn't, Sarah cannot be a manager (contrapositive reasoning).")
q("verbal", "reading-comprehension", M, "Passage: 'Remote work has been shown to increase employee autonomy, but it can also reduce spontaneous collaboration that typically occurs in shared office spaces.' According to the passage, a potential downside of remote work is:",
  [("reduced spontaneous collaboration", True), ("reduced employee autonomy", False), ("increased office costs", False), ("increased spontaneous collaboration", False)],
  "The passage directly names reduced spontaneous collaboration as a downside.")

# ---------------------------------------------------------------------------
# Abstract (21) — represented with text/emoji shape sequences (documented limitation: no
# image-asset pipeline exists yet for the question bank).
# ---------------------------------------------------------------------------

q("abstract", "shape-sequences", E, "What comes next in the sequence? 🔺 🔺🔺 🔺🔺🔺 🔺🔺🔺🔺 ?",
  [("🔺🔺🔺🔺🔺", True), ("🔺🔺🔺", False), ("🔺", False), ("🔺🔺🔺🔺🔺🔺", False)],
  "Each term adds one more triangle than the previous term.")
q("abstract", "shape-sequences", M, "Sequence: ⬛ ⬜ ⬛⬛ ⬜⬜ ⬛⬛⬛ ? Find the next term.",
  [("⬜⬜⬜", True), ("⬛⬛⬛⬛", False), ("⬜⬜", False), ("⬛", False)],
  "The pattern alternates black/white, with the count increasing by one every two terms.")
q("abstract", "shape-sequences", H, "Sequence (count of triangles per term): 1, 2, 4, 8. How many triangles are in the next term?",
  [("16", True), ("12", False), ("10", False), ("32", False)],
  "Each term doubles the previous count: 8 x 2 = 16.")
q("abstract", "odd-one-out", E, "Which shape does not belong: 🔵 🔵 🔵 🔺",
  [("🔺", True), ("🔵 (1st)", False), ("🔵 (2nd)", False), ("🔵 (3rd)", False)],
  "Three shapes are circles; the triangle is the odd one out.")
q("abstract", "odd-one-out", M, "Which does not belong: 🔺🔵, 🔺🔵, 🔵🔺, 🔺🔵",
  [("🔵🔺", True), ("🔺🔵 (1st)", False), ("🔺🔵 (2nd)", False), ("🔺🔵 (3rd)", False)],
  "Three items have the triangle first; one has the order reversed.")
q("abstract", "odd-one-out", H, "Which sequence does not follow the same rule as the others? (a) 2,4,8,16  (b) 3,6,12,24  (c) 5,10,20,40  (d) 5,10,15,20",
  [("(d) 5,10,15,20", True), ("(a) 2,4,8,16", False), ("(b) 3,6,12,24", False), ("(c) 5,10,20,40", False)],
  "Sequences (a), (b), and (c) all double each term. Sequence (d) simply adds 5 each time.")
q("abstract", "rotation", M, "A clock's hour hand points to 3 and is rotated 90 degrees clockwise. Where does it now point?",
  [("6", True), ("9", False), ("12", False), ("3", False)],
  "A 90-degree clockwise rotation on a clock face moves the hour hand forward by 3 hours: 3 -> 6.")
q("abstract", "rotation", H, "A square has a dot at its top-left corner. If the square is rotated 90 degrees clockwise, where is the dot now?",
  [("top-right", True), ("bottom-right", False), ("bottom-left", False), ("top-left", False)],
  "Rotating a square 90 degrees clockwise moves the top-left corner to the top-right position.")
q("abstract", "rotation", E, "An arrow points North (up). If rotated 180 degrees, which direction does it point?",
  [("South (down)", True), ("East", False), ("West", False), ("North (up)", False)],
  "A 180-degree rotation reverses direction completely: North becomes South.")
q("abstract", "abstract-matrices", E, "Pattern: ⬜⬛⬜⬛⬜⬛?. What continues the alternating pattern?",
  [("⬜", True), ("⬛", False), ("⬜⬛", False), ("nothing", False)],
  "The pattern strictly alternates white/black; after ⬛ (6th item) comes ⬜ (7th).")
q("abstract", "abstract-matrices", M, "Grid pattern — Top row: ⬛⬜⬛, Middle row: ⬜⬛⬜, Bottom row: ⬛⬜?. What completes the pattern?",
  [("⬛", True), ("⬜", False), ("both", False), ("neither", False)],
  "This is a checkerboard pattern where adjacent cells always alternate colors.")
q("abstract", "abstract-matrices", H, "Grid pattern where each row has one fewer filled circle than the previous row (Row 1: 🔵🔵, Row 2: 🔵⬜, Row 3: ⬜?). What completes Row 3?",
  [("⬜", True), ("🔵", False), ("both", False), ("neither", False)],
  "Row 1 has 2 filled circles, Row 2 has 1, so Row 3 should have 0 — the final cell must be empty (⬜).")
q("abstract", "mirroring", E, "What is the mirror image of the letter 'b' (reflected left-right)?",
  [("d", True), ("p", False), ("q", False), ("b", False)],
  "Reflecting 'b' left-right produces 'd'.")
q("abstract", "mirroring", M, "What is the mirror image of the word 'MOM' when reflected left-right?",
  [("MOM", True), ("WOW", False), ("MOW", False), ("OMO", False)],
  "M and O are both horizontally symmetric letters, and 'MOM' reads the same forwards and backwards, so its mirror image is unchanged.")
q("abstract", "mirroring", H, "A clock shows 3:15. What time does its mirror image (reflected left-right) show?",
  [("8:45", True), ("8:15", False), ("9:45", False), ("7:45", False)],
  "Mirrored clock time = 11:60 minus the original time: 11:60 - 3:15 = 8:45.")
q("abstract", "pattern-progression", E, "Sequence: •, ••, •••, ••••, ? How many dots come next?",
  [("•••••", True), ("••••", False), ("••", False), ("•", False)],
  "Each term adds one more dot than the previous term (5th term has 5 dots).")
q("abstract", "pattern-progression", H, "Sequence: 🔴🔵, 🔴🔴🔵🔵, 🔴🔴🔴🔵🔵🔵, ? What is the next term?",
  [("🔴🔴🔴🔴🔵🔵🔵🔵", True), ("🔴🔴🔴🔵🔵🔵", False), ("🔴🔴🔵🔵", False), ("🔴🔵🔵🔵", False)],
  "Each term increases the count of each color by one: term 4 has four reds followed by four blues.")
q("abstract", "pattern-progression", E, "Sequence: 1 square, 2 squares, 3 squares, 4 squares. How many squares are in the 5th term?",
  [("5", True), ("4", False), ("6", False), ("8", False)],
  "The count increases by exactly one square per term.")
q("abstract", "spatial-reasoning", M, "A cube is painted red on all faces, then cut into 27 equal smaller cubes (3x3x3). How many small cubes have exactly 2 faces painted?",
  [("12", True), ("8", False), ("6", False), ("24", False)],
  "In a 3x3x3 cube: 8 corner cubes have 3 painted faces, 12 edge cubes have 2, 6 face-center cubes have 1, and 1 center cube has 0.")
q("abstract", "spatial-reasoning", H, "Using the same 3x3x3 painted cube, how many small cubes have exactly 1 face painted?",
  [("6", True), ("8", False), ("12", False), ("1", False)],
  "The 6 face-center small cubes (one per face of the large cube) each have exactly 1 painted face.")
q("abstract", "spatial-reasoning", E, "Using the same 3x3x3 painted cube, how many small cubes have no paint at all?",
  [("1", True), ("0", False), ("6", False), ("8", False)],
  "Only the single cube at the very center of the 3x3x3 cube touches no outer face.")

# ---------------------------------------------------------------------------
# Logical (21)
# ---------------------------------------------------------------------------

q("logical", "syllogisms", E, "All roses are flowers. Some flowers fade quickly. Conclusion: Some roses fade quickly.",
  [("Cannot Say", True), ("True", False), ("False", False)],
  "The fading flowers are not established to overlap with roses specifically — this cannot be validly concluded from the premises.")
q("logical", "syllogisms", M, "All squares are rectangles. All rectangles have four sides. Conclusion: All squares have four sides.",
  [("True", True), ("False", False), ("Cannot Say", False)],
  "This is a valid chain of syllogistic reasoning: squares -> rectangles -> four sides.")
q("logical", "syllogisms", M, "No fish are mammals. All whales are mammals. Conclusion: No whales are fish.",
  [("True", True), ("False", False), ("Cannot Say", False)],
  "Since whales are entirely within the mammal category, and no mammals are fish, no whales can be fish.")
q("logical", "syllogisms", H, "Some doctors are teachers. All teachers are educated. Conclusion: Some doctors are educated.",
  [("True", True), ("False", False), ("Cannot Say", False)],
  "The doctors who are teachers must be educated (since all teachers are), so some doctors are educated.")
q("logical", "syllogisms", E, "Aptitude test convention: treat all premises as true regardless of real-world knowledge. All birds can fly. Penguins are birds. Conclusion: Penguins can fly.",
  [("True", True), ("False", False), ("Cannot Say", False)],
  "Judged purely on the stated premises (not real-world fact), the conclusion follows logically — this is a standard syllogism-testing convention.")
q("logical", "coding-decoding", M, "If CAT is coded as DBU (each letter shifted forward by 1), how is DOG coded using the same rule?",
  [("EPH", True), ("DPH", False), ("EPG", False), ("FPI", False)],
  "Shifting each letter forward by 1: D->E, O->P, G->H, giving EPH.")
q("logical", "coding-decoding", E, "If 'BOOK' is coded as 'CPPL' (each letter shifted forward by 1), what is 'PEN' coded as?",
  [("QFO", True), ("QDM", False), ("OFO", False), ("QFP", False)],
  "Shifting each letter forward by 1: P->Q, E->F, N->O, giving QFO.")
q("logical", "coding-decoding", H, "In a certain code, 'PENCIL' is written as 'QFODJM'. How is 'PAPER' written in the same code?",
  [("QBQFS", True), ("QAQDR", False), ("PBPFS", False), ("QBQES", False)],
  "Each letter is shifted forward by 1: P->Q, A->B, P->Q, E->F, R->S, giving QBQFS.")
q("logical", "blood-relations", E, "Pointing to a man, a woman says, 'His mother is the only daughter of my mother.' How is the woman related to the man?",
  [("Mother", True), ("Sister", False), ("Aunt", False), ("Grandmother", False)],
  "'The only daughter of my mother' is the woman herself, so the woman is the man's mother.")
q("logical", "blood-relations", M, "A is B's brother. C is B's mother. D is C's father. How is A related to D?",
  [("Grandson", True), ("Son", False), ("Nephew", False), ("Brother", False)],
  "C is also A's mother (A and B are siblings), and D is C's father, making D A's grandfather — so A is D's grandson.")
q("logical", "blood-relations", H, "Introducing a boy, a girl said, 'He is the son of my grandfather's only son.' How is the girl related to the boy?",
  [("Sister", True), ("Mother", False), ("Aunt", False), ("Cousin", False)],
  "'My grandfather's only son' is the girl's own father, so the boy is the girl's father's son — her brother, meaning she is his sister.")
q("logical", "logical-series-completion", E, "Find the next letter: A, C, E, G, ?",
  [("I", True), ("H", False), ("J", False), ("F", False)],
  "The sequence skips one letter each time (A, skip B, C, skip D, E...), so after G comes I.")
q("logical", "logical-series-completion", M, "Find the next term: Z, X, V, T, ?",
  [("R", True), ("S", False), ("Q", False), ("U", False)],
  "The sequence moves backward through the alphabet, skipping one letter each time.")
q("logical", "logical-series-completion", H, "Find the missing term: 2, 6, 12, 20, 30, ?",
  [("42", True), ("40", False), ("36", False), ("44", False)],
  "The differences between terms are 4, 6, 8, 10, 12 — each term is n(n+1): 6x7=42.")
q("logical", "logical-deduction", M, "If all members of Team A are engineers, and no engineers are part-time workers, which conclusion must be true?",
  [("No members of Team A are part-time workers", True), ("All part-time workers are engineers", False),
   ("Some engineers are part-time workers", False), ("All engineers are members of Team A", False)],
  "Since Team A members are all engineers, and no engineers are part-time, no Team A member can be part-time.")
q("logical", "logical-deduction", E, "Statement: If it rains, the match will be postponed. It is not raining. Conclusion: The match will not be postponed.",
  [("Cannot Say", True), ("True", False), ("False", False)],
  "This is the 'denying the antecedent' fallacy — the match could still be postponed for another reason, so the conclusion doesn't necessarily follow.")
q("logical", "venn-diagrams", M, "In a survey, 60 people like tea, 40 like coffee, and 20 like both. How many people like at least one of the two drinks?",
  [("80", True), ("100", False), ("60", False), ("40", False)],
  "Using inclusion-exclusion: 60 + 40 - 20 = 80.")
q("logical", "venn-diagrams", H, "In a class of 50 students, 30 play football, 25 play cricket, and 10 play both. How many play neither sport?",
  [("5", True), ("10", False), ("15", False), ("20", False)],
  "Students playing at least one sport = 30+25-10=45. Neither = 50-45=5.")
q("logical", "seating-arrangements", M, "Four friends A, B, C, D sit around a square table, one per side, facing the center. A is opposite C. B is to the immediate right of A. Who is to the immediate left of A?",
  [("D", True), ("B", False), ("C", False), ("A", False)],
  "With A opposite C and B to A's immediate right, the only remaining seat, to A's immediate left, must be D.")
q("logical", "seating-arrangements", H, "Five people sit in a row of 5 seats. B is 2nd from the left. D is immediately to the right of B. A is at one of the ends. C is immediately to the left of A. E fills the remaining seat. What is the left-to-right order?",
  [("E, B, D, C, A", True), ("A, B, D, C, E", False), ("E, B, C, D, A", False), ("B, E, D, C, A", False)],
  "B=2, D=3 (right of B). If A were at position 1, nothing could be left of it, so A=5 and C=4 (left of A). The only remaining seat, position 1, goes to E.")

# ---------------------------------------------------------------------------
# Technical (32) — Mechanical/Process, Data/Analytics, General workplace
# ---------------------------------------------------------------------------

q("technical", "pumps", E, "What is the primary function of a centrifugal pump?",
  [("To convert rotational kinetic energy into hydrodynamic energy to move fluid", True),
   ("To compress gas", False), ("To measure flow rate", False), ("To generate electricity", False)],
  "A centrifugal pump uses a rotating impeller to increase fluid velocity, converting kinetic energy into flow.")
q("technical", "pumps", M, "Cavitation in a centrifugal pump is most commonly caused by:",
  [("Insufficient net positive suction head (NPSH)", True), ("Excessive discharge pressure", False),
   ("Too much suction pressure", False), ("An oversized impeller", False)],
  "Cavitation occurs when local pressure drops below the fluid's vapor pressure, typically from insufficient NPSH.")
q("technical", "valves", E, "Which valve type is best suited for fully open/fully closed on-off service rather than throttling?",
  [("Gate valve", True), ("Globe valve", False), ("Control valve", False), ("Needle valve", False)],
  "Gate valves are designed for full-open/full-closed service, not for precise flow throttling.")
q("technical", "valves", M, "A check valve is primarily used to:",
  [("Prevent backflow in a pipeline", True), ("Regulate flow rate precisely", False),
   ("Measure pressure", False), ("Mix two fluids", False)],
  "Check valves allow flow in only one direction, preventing reverse flow.")
q("technical", "compressors", M, "In a reciprocating compressor, 'clearance volume' refers to:",
  [("The volume remaining in the cylinder at the end of the compression stroke", True),
   ("The total swept volume of the piston", False), ("The volume of the discharge pipe", False),
   ("The volume of lubricant used", False)],
  "Clearance volume is the small residual volume left when the piston is at top dead center.")
q("technical", "p-and-ids", E, "What does 'P&ID' stand for in process engineering?",
  [("Piping and Instrumentation Diagram", True), ("Process and Inventory Design", False),
   ("Pump and Instrument Data", False), ("Pressure and Impact Diagram", False)],
  "A P&ID shows the piping, equipment, and instrumentation of a process system.")
q("technical", "dcs", M, "What is the main purpose of a Distributed Control System (DCS) in a process plant?",
  [("To centrally monitor and control plant processes while distributing processing across multiple controllers", True),
   ("To physically distribute raw materials", False), ("To replace all field instrumentation", False),
   ("To manage employee schedules", False)],
  "A DCS distributes control functions across networked controllers while providing centralized monitoring.")
q("technical", "scada", M, "SCADA systems are primarily used for:",
  [("Supervisory control and data acquisition over geographically dispersed assets", True),
   ("Manual valve operation only", False), ("Employee payroll processing", False), ("3D modeling of equipment", False)],
  "SCADA (Supervisory Control And Data Acquisition) monitors and controls dispersed industrial assets.")
q("technical", "instrumentation", E, "Which instrument is used to measure fluid flow rate in a pipeline?",
  [("Flow meter", True), ("Thermocouple", False), ("Pressure gauge", False), ("Tachometer", False)],
  "A flow meter directly measures the rate of fluid movement through a pipe.")
q("technical", "loto", M, "What does LOTO stand for in workplace safety procedures?",
  [("Lockout/Tagout", True), ("Load Out, Turn Off", False), ("Line Out, Track Output", False),
   ("Local Operations Testing Order", False)],
  "LOTO (Lockout/Tagout) isolates energy sources before maintenance to protect workers.")
q("technical", "flow", M, "Using the continuity equation, if a pipe's cross-sectional area decreases by half while flow rate remains constant, the fluid velocity will:",
  [("Double", True), ("Halve", False), ("Stay the same", False), ("Quadruple", False)],
  "A1V1=A2V2 — halving the area requires doubling the velocity to keep flow rate constant.")
q("technical", "pressure", E, "What unit is commonly used to measure pressure in process industries?",
  [("psi (pounds per square inch) or bar", True), ("Newton-meters", False), ("Watts", False), ("Amperes", False)],
  "Pressure in process industries is commonly measured in psi or bar.")
q("technical", "temperature", M, "Which temperature scale is standard for engineering thermodynamic calculations because it starts at absolute zero?",
  [("Kelvin", True), ("Celsius", False), ("Fahrenheit", False), ("Reaumur", False)],
  "Kelvin is the SI absolute temperature scale, starting at absolute zero, used in thermodynamic formulas.")
q("technical", "heat-exchangers", M, "In a shell-and-tube heat exchanger, counter-current flow compared to co-current (parallel) flow generally provides:",
  [("A higher overall temperature difference and better heat transfer efficiency", True),
   ("Lower efficiency", False), ("No difference in performance", False), ("Only works with gases", False)],
  "Counter-current flow maintains a more favorable temperature gradient along the exchanger's length, improving efficiency.")
q("technical", "separators", M, "What is the primary function of a two-phase separator in an oil and gas facility?",
  [("To separate liquid and gas phases from a production stream", True), ("To separate oil from water only", False),
   ("To compress natural gas", False), ("To heat crude oil", False)],
  "A two-phase separator splits a mixed production stream into its liquid and gas components.")
q("technical", "troubleshooting", H, "A centrifugal pump is running but producing no flow. What should a technician check FIRST?",
  [("Whether the pump has been properly primed (no air lock/vapor lock)", True),
   ("The color of the pump casing", False), ("The pump's serial number", False),
   ("The plant's overall production schedule", False)],
  "A common cause of a running-but-not-pumping centrifugal pump is an unprimed pump or air/vapor lock.")
q("technical", "fluid-mechanics", H, "Bernoulli's principle states that as the velocity of a fluid increases (for incompressible, non-viscous flow along a streamline):",
  [("Its pressure decreases", True), ("Its pressure increases", False), ("Its temperature always increases", False),
   ("Its density always increases", False)],
  "Bernoulli's principle describes an inverse relationship between fluid velocity and pressure along a streamline.")
q("technical", "thermodynamics", H, "The First Law of Thermodynamics is essentially a statement of:",
  [("Conservation of energy", True), ("Conservation of momentum", False), ("Entropy always increasing", False),
   ("Conservation of mass only", False)],
  "The First Law states energy cannot be created or destroyed, only converted between forms.")
q("technical", "sql", E, "Which SQL clause is used to filter rows based on a condition?",
  [("WHERE", True), ("ORDER BY", False), ("GROUP BY", False), ("SELECT", False)],
  "The WHERE clause filters rows that meet a specified condition.")
q("technical", "sql", M, "Which SQL function would you use to count the number of rows in a table?",
  [("COUNT()", True), ("SUM()", False), ("AVG()", False), ("LEN()", False)],
  "COUNT() returns the number of rows matching a query.")
q("technical", "excel", E, "In a spreadsheet, which function calculates the average of a range of cells?",
  [("AVERAGE()", True), ("SUM()", False), ("COUNT()", False), ("MEDIAN()", False)],
  "AVERAGE() computes the arithmetic mean of a range of values.")
q("technical", "statistics", M, "What does a p-value of 0.03 typically indicate in a hypothesis test at a 0.05 significance level?",
  [("The result is statistically significant", True), ("The result is not significant", False),
   ("The sample size was too small", False), ("The hypothesis is definitely true", False)],
  "Since 0.03 is below the 0.05 threshold, the result is considered statistically significant.")
q("technical", "technical-data-interpretation", M, "A bar chart shows Q1 sales of $50,000 and Q2 sales of $65,000. What is the percentage growth from Q1 to Q2?",
  [("30%", True), ("20%", False), ("25%", False), ("35%", False)],
  "Growth = (65,000-50,000)/50,000 = 30%.")
q("technical", "visualization", E, "Which chart type is generally best for showing the proportion of categories within a whole?",
  [("Pie chart", True), ("Line chart", False), ("Scatter plot", False), ("Histogram", False)],
  "Pie charts are designed to show how categories make up a whole.")
q("technical", "probability", M, "If a fair six-sided die is rolled once, what is the probability of rolling a number greater than 4?",
  [("1/3", True), ("1/2", False), ("1/6", False), ("2/3", False)],
  "Numbers greater than 4 are 5 and 6 — 2 out of 6 outcomes = 1/3.")
q("technical", "statistics", H, "A dataset has a mean of 50 and a standard deviation of 5. Approximately what percentage of data falls within one standard deviation of the mean, assuming a normal distribution?",
  [("68%", True), ("95%", False), ("99.7%", False), ("50%", False)],
  "The empirical rule states about 68% of normally distributed data falls within one standard deviation of the mean.")
q("technical", "computer-literacy", E, "What is the primary purpose of antivirus software?",
  [("To detect and remove malicious software from a computer", True), ("To speed up internet connection", False),
   ("To create backups automatically", False), ("To design websites", False)],
  "Antivirus software scans for, detects, and removes malware.")
q("technical", "ms-office", E, "In a word processor, which keyboard shortcut is commonly used to save a document?",
  [("Ctrl+S", True), ("Ctrl+P", False), ("Ctrl+C", False), ("Ctrl+Z", False)],
  "Ctrl+S is the standard save shortcut across most word processors.")
q("technical", "email-etiquette", E, "When emailing multiple recipients, when should 'Reply All' typically be used?",
  [("Only when the response is relevant to everyone on the thread", True), ("Always, regardless of relevance", False),
   ("Never", False), ("Only for urgent messages", False)],
  "'Reply All' should be reserved for responses genuinely relevant to the whole group, to avoid inbox clutter.")
q("technical", "cybersecurity-basics", M, "Which of the following is a common sign of a phishing email?",
  [("Urgent requests for personal information from an unfamiliar or suspicious sender", True),
   ("A properly formatted company logo", False), ("An email from a known colleague about a scheduled meeting", False),
   ("A newsletter you subscribed to", False)],
  "Phishing emails often create urgency and request sensitive information from unfamiliar senders.")
q("technical", "cybersecurity-basics", M, "What is the main purpose of two-factor authentication (2FA)?",
  [("To add an extra layer of security beyond just a password", True), ("To make login faster", False),
   ("To allow password sharing safely", False), ("To remove the need for passwords entirely", False)],
  "2FA requires a second verification factor in addition to a password, improving account security.")
q("technical", "project-management-basics", M, "In project management, what does the term 'scope creep' refer to?",
  [("Uncontrolled expansion of a project's scope without corresponding adjustments to time, cost, or resources", True),
   ("A well-documented change request process", False), ("Reducing the number of project tasks", False),
   ("Finishing a project ahead of schedule", False)],
  "Scope creep describes scope expanding beyond the original plan without matching adjustments to resources or schedule.")

# ---------------------------------------------------------------------------
# Situational Judgement (16)
# ---------------------------------------------------------------------------

q("situational-judgement", "workplace-scenarios", E, "You notice a coworker taking credit for your idea in a team meeting. What is the most professional response?",
  [("Speak with the coworker privately afterward to address the issue directly", True),
   ("Complain loudly in the meeting", False), ("Say nothing and let it go entirely", False),
   ("Immediately report to HR without talking to the coworker first", False)],
  "Addressing the issue directly and privately is the most professional first step before escalating.")
q("situational-judgement", "customer-service", M, "A customer is visibly upset about a delayed order and raises their voice. What should you do first?",
  [("Listen calmly and acknowledge their frustration before offering a solution", True),
   ("End the conversation immediately", False), ("Argue that the delay wasn't your fault", False),
   ("Transfer them without explanation", False)],
  "De-escalating by listening and acknowledging frustration is the standard first step in customer service.")
q("situational-judgement", "time-management", M, "You are assigned a task with a deadline you know is unrealistic. What is the best course of action?",
  [("Raise the concern with your supervisor as soon as possible, explaining why and proposing alternatives", True),
   ("Say nothing and miss the deadline", False), ("Do a rushed, low-quality job to meet the deadline", False),
   ("Refuse the task outright", False)],
  "Proactively communicating concerns early gives the best chance to adjust scope, resources, or timeline.")
q("situational-judgement", "teamwork", E, "A team member is consistently late to meetings, affecting team productivity. What is the best approach?",
  [("Speak to them privately and understand the reason before escalating", True),
   ("Publicly criticize them in the next meeting", False), ("Ignore the issue", False),
   ("Immediately report them to management without discussion", False)],
  "A private, understanding conversation is the appropriate first step before escalation.")
q("situational-judgement", "ethics-integrity", M, "You discover a minor error in a report that has already been sent to a client. What should you do?",
  [("Notify your supervisor and correct the error with the client as soon as possible", True),
   ("Ignore it since it's minor", False), ("Wait to see if the client notices", False),
   ("Blame a colleague for the mistake", False)],
  "Transparency and prompt correction maintain trust and professionalism, even for minor errors.")
q("situational-judgement", "ethics-integrity", H, "Your manager asks you to complete a task in a way that conflicts with company policy. What should you do?",
  [("Politely raise the concern with your manager and seek clarification or escalate if needed", True),
   ("Comply without question", False), ("Refuse and report your manager immediately without discussion", False),
   ("Ignore the manager's instructions silently", False)],
  "Raising the concern directly first is the appropriate professional response before escalating further.")
q("situational-judgement", "teamwork", M, "You are working on a team project and a teammate is not contributing their fair share. What is the best first step?",
  [("Have a direct, respectful conversation with the teammate about expectations", True),
   ("Complete their work for them without saying anything", False),
   ("Complain to the rest of the team behind their back", False),
   ("Report them to management immediately without speaking to them first", False)],
  "A direct conversation addressing expectations is the appropriate first step in resolving team contribution issues.")
q("situational-judgement", "customer-service", E, "A customer asks for a refund outside of the standard policy. What should you do?",
  [("Explain the policy clearly and check if there's an exception process, escalating if needed", True),
   ("Immediately refuse with no explanation", False), ("Give the refund regardless of policy", False),
   ("Ignore the request", False)],
  "Clear communication and checking for legitimate exceptions balances policy adherence with good service.")
q("situational-judgement", "ethics-integrity", M, "You realize you made a mistake that could cost the company money. What is the best action?",
  [("Report it immediately to your supervisor so it can be addressed", True), ("Hope no one notices", False),
   ("Try to fix it secretly without telling anyone", False), ("Blame the system for the error", False)],
  "Prompt, honest reporting allows the issue to be addressed quickly and limits potential damage.")
q("situational-judgement", "conflict-resolution", M, "Two colleagues are in a heated disagreement during a meeting, disrupting the discussion. As the facilitator, what should you do?",
  [("Calmly pause the discussion and redirect focus to finding common ground", True),
   ("Let them continue arguing until one gives up", False), ("Take one side publicly", False),
   ("End the meeting immediately without resolution", False)],
  "A calm, neutral intervention that redirects toward common ground is the most constructive facilitation approach.")
q("situational-judgement", "ethics-integrity", H, "You are given confidential information about an upcoming company decision that isn't public yet. A close friend asks if you know anything about it. What should you do?",
  [("Politely decline to share confidential information, even with a friend", True),
   ("Tell them since they're a close friend", False), ("Hint at the information indirectly", False),
   ("Share it but ask them to keep it secret", False)],
  "Maintaining confidentiality applies regardless of personal relationships.")
q("situational-judgement", "time-management", E, "You have multiple urgent tasks due at the same time. What is the best approach?",
  [("Prioritize tasks based on deadlines and business impact, communicating with stakeholders if needed", True),
   ("Work on whichever task you find most interesting", False), ("Panic and do nothing", False),
   ("Ignore some tasks without telling anyone", False)],
  "Prioritizing by impact and communicating proactively is the most effective way to manage competing urgent tasks.")
q("situational-judgement", "workplace-scenarios", M, "A new team member seems overwhelmed and hesitant to ask for help. What should you do?",
  [("Proactively check in with them and offer support", True),
   ("Wait for them to ask, even if they seem to be struggling", False),
   ("Assume they'll figure it out on their own", False), ("Report them as underperforming immediately", False)],
  "Proactively offering support helps new team members without waiting for them to struggle further.")
q("situational-judgement", "workplace-scenarios", M, "You notice a safety hazard on the work floor that could injure someone. What is the best immediate action?",
  [("Address or flag the hazard immediately and report it to the appropriate person", True),
   ("Ignore it since it's not your responsibility", False), ("Wait until your shift ends to mention it", False),
   ("Only mention it if someone gets hurt", False)],
  "Safety hazards should always be addressed or reported immediately to prevent injury.")
q("situational-judgement", "ethics-integrity", H, "You are asked to falsify a minor detail in a report to make results look better for a client presentation. What should you do?",
  [("Decline and explain that falsifying data is against company ethics and could have serious consequences", True),
   ("Falsify it since it's minor", False), ("Do it but tell a colleague afterward", False),
   ("Falsify it only if no one will find out", False)],
  "Data integrity should never be compromised, regardless of how minor the falsification seems.")
q("situational-judgement", "workplace-scenarios", E, "You receive feedback from your manager that is difficult to hear but constructive. What is the best response?",
  [("Listen openly, ask clarifying questions, and use it to improve", True),
   ("Get defensive and argue", False), ("Ignore the feedback entirely", False),
   ("Complain about the manager to coworkers", False)],
  "Receiving constructive feedback openly and acting on it is the most professional and growth-oriented response.")


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(Question).where(Question.is_demo.is_(True)))).scalars().first()
        if existing is not None:
            print("Demo aptitude questions already present — skipping seed.")
            return

        categories_by_slug: dict[str, QuestionCategory] = {}
        for data in CATEGORIES:
            category = QuestionCategory(**data)
            db.add(category)
            await db.flush()
            categories_by_slug[data["slug"]] = category
            print(f"Created category: {category.name}")

        topics_by_slug: dict[str, QuestionTopic] = {}
        for category_slug, name, slug, field, industry in TOPICS:
            topic = QuestionTopic(
                category_id=categories_by_slug[category_slug].id,
                name=name,
                slug=slug,
                field=field,
                industry=industry,
            )
            db.add(topic)
            await db.flush()
            topics_by_slug[slug] = topic
        print(f"Created {len(topics_by_slug)} topics.")

        created = 0
        for category_slug, topic_slug, difficulty, qtype, text, options, explanation, passage, numeric in QUESTIONS:
            topic = topics_by_slug[topic_slug] if topic_slug else None
            question = Question(
                question_text=text,
                question_type=qtype,
                passage_text=passage,
                category_id=categories_by_slug[category_slug].id,
                topic_id=topic.id if topic else None,
                field=topic.field if topic else None,
                industry=topic.industry if topic else None,
                difficulty=difficulty,
                explanation=explanation,
                marks=1.0,
                negative_marks=0.25,
                is_active=True,
                is_demo=True,
                correct_numeric_value=numeric[0] if numeric else None,
                numeric_tolerance=numeric[1] if numeric else 0.0,
            )
            db.add(question)
            await db.flush()

            if options:
                for order, (option_text, is_correct) in enumerate(options):
                    db.add(
                        QuestionOption(
                            question_id=question.id,
                            option_text=option_text,
                            is_correct=is_correct,
                            display_order=order,
                        )
                    )
            created += 1

        await db.commit()
        print(f"Seeded {created} demo aptitude questions across {len(categories_by_slug)} categories.")


if __name__ == "__main__":
    asyncio.run(seed())
