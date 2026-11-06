"""Gemini prompts and response schemas for the AI Learning Hub.

Every call returns validated structured JSON (pydantic) or raises
``GeminiUnavailable``. Prompts forbid invented URLs, statistics and citations:
resources are returned as *search suggestions*, never links.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.careerverse import gemini_service as g

NO_FABRICATION = (
    "Rules: Never invent URLs, links, statistics, studies, book page numbers or citations. "
    "If you suggest a resource, give only its name and a web-search query, and say nothing about its contents you are not sure of. "
    "Be accurate; if unsure, say so plainly."
)
Difficulty = Literal["easy", "medium", "hard"]


class Lenient(BaseModel):
    """Accepts the small shape slips LLMs make: a string where a list is wanted, or null for an empty list."""

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for name, f in cls.model_fields.items():
                if "list" not in str(f.annotation):
                    continue
                key = f.alias or name
                v = data.get(key, data.get(name))
                if v is None and (key in data or name in data):
                    data[key] = []
                elif isinstance(v, str):
                    lines = [x.strip("-*• \t") for x in v.split("\n") if x.strip("-*• \t")]
                    data[key] = lines or ([v] if v.strip() else [])
        return data


# ------------------------------------------------------------------ plan units
class ResourceHint(Lenient):
    kind: str = "reference"
    name: str
    search_query: str = ""


class UnitSchema(Lenient):
    title: str
    topic: str
    subtopics: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    assignment: str = ""
    est_minutes: int = Field(ge=15, le=480)
    difficulty: Difficulty = "medium"
    category: Literal["learn", "practice", "project"] = "learn"
    resources: list[ResourceHint] = Field(default_factory=list)

    @field_validator("subtopics", "objectives", mode="before")
    @classmethod
    def _cap(cls, v: Any) -> Any:
        return v[:8] if isinstance(v, list) else v


class UnitList(Lenient):
    units: list[UnitSchema] = Field(min_length=1)


def phase_units(*, role: str, level: str, phase_title: str, phase_key: str, budget_minutes: int, candidates: list[dict[str, Any]],
                already_covered: list[str], focus: list[str], companies: list[str], weak_topics: list[str], notes: str, daily_minutes: int) -> list[dict[str, Any]]:
    """Ask Gemini for the ordered study units of ONE phase, sized to a minute budget."""
    ask = (
        f"You design a personalised learning journey for a student targeting: {role}. Their starting level is: {level}.\n"
        f"Create the ordered study units for the '{phase_title}' phase. Total study time across units must be about {budget_minutes} minutes "
        f"(between {int(budget_minutes * 0.85)} and {int(budget_minutes * 1.1)}). Each unit should fit within about {daily_minutes} minutes; "
        "a unit may be longer only if it is a project.\n"
        + ("This is the PROJECTS phase: design 2-4 portfolio projects (category 'project') of increasing scope that apply earlier topics; each project needs a clear deliverable in 'assignment'.\n" if phase_key == "projects" else
           "Use the candidate topics below as the backbone (respect their prerequisite order), split big topics into units, "
           "add 'practice' units for hands-on work, and skip nothing that is a prerequisite. You may add closely related topics a role-ready learner needs.\n")
        + f"Candidate topics (title, subject, rough hours, prerequisites): {json.dumps(candidates)}\n"
        f"Already known or covered earlier (do NOT re-teach): {json.dumps(already_covered[:40])}\n"
        f"Learner focus areas: {json.dumps(focus)}. Target companies: {json.dumps(companies)}. Topics they struggled with: {json.dumps(weak_topics)}.\n"
        f"Learner notes: {notes[:500] or 'none'}\n"
        "Return JSON {\"units\": [{\"title\": str, \"topic\": str, \"subtopics\": [str], \"objectives\": [str], \"assignment\": str (a concrete practical task), "
        "\"est_minutes\": int, \"difficulty\": \"easy|medium|hard\", \"category\": \"learn|practice|project\", "
        "\"resources\": [{\"kind\": \"docs|video|book|practice|reference\", \"name\": str, \"search_query\": str}]}]}. "
        f"{NO_FABRICATION}"
    )
    return g.generate_json(ask, schema=UnitList, temperature=0.5, max_tokens=7000, retries=3)["units"]


class GapExplanation(Lenient):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    priority_gaps: list[str] = Field(default_factory=list)
    advice: list[str] = Field(default_factory=list)


def explain_gap(role: str, level: str, matched: list[str], missing: list[str]) -> dict[str, Any]:
    ask = (
        f"Explain, for a student targeting '{role}', their skill gap using ONLY this analysis. Starting level: {level}. "
        f"Topics their profile already supports: {json.dumps(matched[:25])}. Topics not yet evidenced: {json.dumps(missing[:25])}. "
        "Return JSON {\"summary\": 2-3 sentences, \"strengths\": [<=4], \"priority_gaps\": [<=5], \"advice\": [<=4 short actions]}. Do not invent facts about the student. "
        + NO_FABRICATION
    )
    return g.generate_json(ask, schema=GapExplanation, temperature=0.3, max_tokens=700)


# ------------------------------------------------------------------ study material
class Section(Lenient):
    heading: str
    body: str


class CodeSnippet(Lenient):
    title: str = ""
    language: str = "text"
    code: str
    explanation: str = ""


class PracticeProblem(Lenient):
    question: str
    hint: str = ""
    answer: str = ""


class Material(Lenient):
    title: str
    summary: str
    definitions: list[Section] = Field(default_factory=list)
    explanation: list[Section] = Field(min_length=1)
    examples: list[Section] = Field(default_factory=list)
    code_snippets: list[CodeSnippet] = Field(default_factory=list)
    formulas: list[Section] = Field(default_factory=list)
    real_world_applications: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    interview_relevance: list[str] = Field(default_factory=list)
    practice_problems: list[PracticeProblem] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    revision_summary: str = ""
    sources: list[str] = Field(default_factory=list)


DEPTH_HINT = {"brief": "concise, about 400 words", "standard": "thorough, about 900 words", "deep": "in-depth, about 1600 words"}


def material(topic: str, level: str, depth: str, learner_context: str = "", extra: str = "", base: dict[str, Any] | None = None) -> dict[str, Any]:
    ask = (
        f"Write complete study notes on: {topic}\nAudience level: {level}. Style: {DEPTH_HINT.get(depth, DEPTH_HINT['standard'])}. {extra}\n"
        f"Learner context (use to tailor examples, do not mention it): {learner_context[:600] or 'none'}\n"
        + (f"Previous version to build on:\n{json.dumps(base)[:6000]}\n" if base else "")
        + "Return JSON with keys: title, summary, definitions[{heading,body}], explanation[{heading,body}] (beginner to advanced, in order), examples[{heading,body}], "
        "code_snippets[{title,language,code,explanation}] (only if the topic is technical), formulas[{heading,body}] (only if relevant; plain text math), "
        "real_world_applications[str], common_mistakes[str], interview_relevance[str], practice_problems[{question,hint,answer}], key_takeaways[str], revision_summary (<=120 words), sources[str]. "
        "Use empty arrays for sections that do not apply. 'sources' may name well-known reference works by title only, or be empty. Code must be correct and runnable. "
        + NO_FABRICATION
    )
    return g.generate_json(ask, schema=Material, temperature=0.5, max_tokens=7500, retries=3)


class Node(Lenient):
    id: str
    label: str


class Edge(Lenient):
    source: str = Field(alias="from")
    target: str = Field(alias="to")
    label: str = ""

    model_config = {"populate_by_name": True}


class Diagram(Lenient):
    title: str
    description: str = ""
    nodes: list[Node] = Field(min_length=2, max_length=16)
    edges: list[Edge] = Field(default_factory=list)


def diagram(topic: str, level: str) -> dict[str, Any]:
    ask = (
        f"Create a clear concept diagram for: {topic} (level: {level}). Return JSON {{\"title\": str, \"description\": 1-2 sentences, "
        "\"nodes\": [{\"id\": short id, \"label\": <=5 words}] (4-12 nodes), \"edges\": [{\"from\": id, \"to\": id, \"label\": <=3 words}]}. "
        "Show real structure (flow, hierarchy or relationships). Every edge must reference existing node ids. " + NO_FABRICATION
    )
    data = g.generate_json(ask, schema=Diagram, temperature=0.3, max_tokens=1200)
    ids = {n["id"] for n in data["nodes"]}
    data["edges"] = [e for e in data["edges"] if e.get("source", e.get("from")) in ids and e.get("target", e.get("to")) in ids]
    return data


class FollowUp(Lenient):
    answer: str


def follow_up(topic: str, level: str, material_json: dict[str, Any], question: str) -> str:
    ask = (
        f"A student studying '{topic}' (level {level}) asks a follow-up question. Answer clearly and accurately using the notes as context, "
        "adding new detail when needed. Use short paragraphs and, where useful, a small code example in markdown fences. "
        f"Return JSON {{\"answer\": str}}.\nNOTES: {json.dumps(material_json)[:5000]}\nQUESTION: {question[:800]}\n" + NO_FABRICATION
    )
    return g.generate_json(ask, schema=FollowUp, temperature=0.4, max_tokens=1500)["answer"]


# ------------------------------------------------------------------ YouTube
class Chapter(Lenient):
    title: str
    start_seconds: int = 0
    summary: str
    key_points: list[str] = Field(default_factory=list)


class Flashcard(Lenient):
    front: str
    back: str


class VideoQuestion(Lenient):
    question: str
    options: list[str] = Field(min_length=3, max_length=5)
    answer_index: int = Field(ge=0)
    explanation: str = ""


class Concept(Lenient):
    name: str
    explanation: str
    why_it_matters: str = ""
    timestamp_seconds: int | None = None


class Term(Lenient):
    term: str
    definition: str


class Application(Lenient):
    area: str
    description: str


class VideoSummary(Lenient):
    overview: str
    level: str = ""
    topics: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    concepts: list[Concept] = Field(default_factory=list)
    terminology: list[Term] = Field(default_factory=list)
    applications: list[Application] = Field(default_factory=list)
    tools_mentioned: list[str] = Field(default_factory=list)
    chapters: list[Chapter] = Field(min_length=1)
    key_concepts: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    takeaways: list[str] = Field(default_factory=list)
    flashcards: list[Flashcard] = Field(default_factory=list)
    quiz: list[VideoQuestion] = Field(default_factory=list)


def summarise_video(title: str, transcript_text: str) -> dict[str, Any]:
    ask = (
        f"Turn this video transcript into well-organised study notes. Video title: {title or 'unknown'}.\n"
        "Transcript lines look like [seconds] text. Base EVERYTHING on what the speaker actually said; do not add outside facts. "
        "If the video does not cover a section (for example no real-world applications), return an empty list for it instead of inventing content.\n"
        "Return JSON {\"overview\": 2-3 sentence summary, \"level\": \"beginner|intermediate|advanced\" (as taught), \"topics\": [main subjects], "
        "\"prerequisites\": [what a viewer should already know, only if implied], "
        "\"concepts\": [{\"name\": str, \"explanation\": clear 2-3 sentences, \"why_it_matters\": 1 sentence, \"timestamp_seconds\": int from the transcript or null}] (the core ideas to learn, 4-10), "
        "\"terminology\": [{\"term\": str, \"definition\": plain-language definition as used in the video}] (every important term, 6-20), "
        "\"applications\": [{\"area\": where or how it is used, \"description\": str}] (only those mentioned or clearly shown), "
        "\"tools_mentioned\": [tools, libraries, products named], "
        "\"chapters\": [{\"title\": str, \"start_seconds\": int, \"summary\": str, \"key_points\": [str]}], "
        "\"key_concepts\": [one-line recap items], \"examples\": [worked examples from the video], \"takeaways\": [actionable lessons], "
        "\"flashcards\": [{\"front\": str, \"back\": str}] (6-10), "
        "\"quiz\": [{\"question\": str, \"options\": [3-4 str], \"answer_index\": int, \"explanation\": str}] (5 questions)}.\n"
        f"TRANSCRIPT:\n{transcript_text[:60000]}"
    )
    data = g.generate_json(ask, schema=VideoSummary, temperature=0.3, max_tokens=8000, retries=3)
    for q in data["quiz"]:
        q["answer_index"] = min(q["answer_index"], len(q["options"]) - 1)
    return data


# ------------------------------------------------------------------ quizzes
class QuestionSchema(Lenient):
    qtype: Literal["mcq", "true_false", "output_prediction", "code_tracing", "short_answer", "scenario", "coding", "debugging"]
    difficulty: Difficulty = "medium"
    topic: str
    subtopic: str = ""
    prompt: str
    options: list[str] = Field(default_factory=list)
    answer_index: int | None = None
    answer_bool: bool | None = None
    answer_text: str | None = None
    alternatives: list[str] = Field(default_factory=list)
    explanation: str = ""
    rubric: list[dict[str, Any]] = Field(default_factory=list)
    entry_function: str | None = None
    starter_code: str | None = None
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    reference_solution: str | None = None


class QuestionList(Lenient):
    questions: list[QuestionSchema] = Field(min_length=1)


def quiz_questions(*, topic: str, scope_note: str, count: int, difficulty: str, types: list[str], level: str, weak: list[str], language: str) -> list[dict[str, Any]]:
    ask = (
        f"Write {count} NEW assessment questions on: {topic}. {scope_note}\nStudent level: {level}. Difficulty: {difficulty} "
        "(if 'mixed', use a spread of easy, medium and hard and label each).\n"
        f"Use these question types, mixed sensibly: {', '.join(types)}.\n"
        f"Emphasise these weak areas where relevant: {json.dumps(weak)}.\n"
        "Return JSON {\"questions\": [{\"qtype\": str, \"difficulty\": \"easy|medium|hard\", \"topic\": str, \"subtopic\": str, \"prompt\": str, "
        "\"options\": [str] (mcq only, 4 options), \"answer_index\": int (mcq), \"answer_bool\": bool (true_false), "
        "\"answer_text\": str (output_prediction / code_tracing exact expected output), \"alternatives\": [str] (other accepted spellings), "
        "\"explanation\": str (why the answer is right and common wrong turns), "
        "\"rubric\": [{\"criterion\": str, \"marks\": number}] (short_answer / scenario / debugging only, 2-4 criteria), "
        f"\"entry_function\": str, \"starter_code\": str, \"reference_solution\": str (a correct, complete Python implementation that passes every test case), \"test_cases\": [{{\"args\": [json values], \"expected\": json value}}] (coding / debugging only; {language}; 4-6 deterministic cases; the function must be pure and use only the standard library)}}]}}. "
        "Questions must be unambiguous with exactly one correct answer where objective. For output_prediction/code_tracing give code in the prompt. "
        "For coding questions the learner writes a Python function named entry_function. " + NO_FABRICATION
    )
    return g.generate_json(ask, schema=QuestionList, temperature=0.6, max_tokens=7500, retries=3)["questions"]
