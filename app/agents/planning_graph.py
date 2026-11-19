"""Planning, execution and verification graph.

Unlike the tool-calling agent, this graph solves open-ended tasks:

    planner -> executor -> synthesizer -> verifier
                               ^             |
                               +-- revise ---+
                                             |
                                         approval (human)
                                          /        \\
                                     finalize     rejected

The planner decomposes the task, the executor gathers evidence with the
existing retrieval service, the synthesizer writes a deliverable, the
verifier checks it and can send it back once for a revision, and a human
must approve the result before it is released.
"""

from __future__ import annotations

import json
import re
from typing import Literal, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.services.answer_cleanup import (
    clean_model_answer,
)

PLANNER_SYSTEM_PROMPT = """
You are the planning module of a knowledge platform.

Decompose the user's task into a short, executable plan that can be solved
with an internal document search tool. Return JSON only, with this shape:

{
  "summary": "one sentence describing the deliverable",
  "steps": [
    {
      "id": 1,
      "title": "short imperative title",
      "action": "search_knowledge",
      "query": "the exact search query for this step"
    }
  ],
  "dependencies": ["ordering or data dependencies between steps"],
  "risks": ["concrete risks or missing information"]
}

Rules:
- Use 3 to 5 steps.
- At least two steps must use action "search_knowledge".
- The remaining steps use action "analyze" or "draft".
- Every "title" and every "query" MUST be written in the same language as the
  task. If the task is English, the queries are English. Never translate the
  query into Chinese, Japanese, Korean, Russian or any other language.
- Search queries must be specific and use the vocabulary of company policies
  (for example "onboarding support engineer access").
- Do not invent facts about the company.
- Return only the JSON object, with no markdown fences.
""".strip()

NON_LATIN_PATTERN = re.compile(
    r"[\u0400-\u04ff\u0600-\u06ff\u3040-\u30ff"
    r"\u4e00-\u9fff\uac00-\ud7af]"
)

SYNTHESIZER_SYSTEM_PROMPT = """
You are a senior analyst writing an internal deliverable.

Use only the evidence provided. If the evidence is insufficient for a
section, say so explicitly instead of inventing details.

Structure the answer with headings and bullet points. Be concrete: name
documents, numbers and owners when the evidence contains them. Finish with
a short "Open questions" section when assumptions remain.
""".strip()

VERIFIER_SYSTEM_PROMPT = """
You are an independent reviewer.

Check the draft against the task and the evidence. Look for unsupported
claims, missing required sections and contradictions. Return JSON only:

{
  "passed": true,
  "confidence": 0.0,
  "issues": ["specific issue"],
  "critique": "two or three sentences of feedback"
}

Rules:
- confidence is between 0 and 1.
- passed is true only when every material claim is supported by the evidence
  and the deliverable answers the task.
- Return only the JSON object, with no markdown fences.
""".strip()

ALLOWED_ACTIONS = {
    "search_knowledge",
    "analyze",
    "draft",
}

MAX_EVIDENCE_ITEMS = 8
MAX_STEPS = 5


class PlanStep(TypedDict):
    id: int
    title: str
    action: Literal[
        "search_knowledge",
        "analyze",
        "draft",
    ]
    query: str
    status: NotRequired[str]
    evidence_count: NotRequired[int]


class PlanEvidence(TypedDict):
    step_id: int
    document_id: int
    position: int
    similarity: float
    content: str


class PlanningState(TypedDict):
    task: str
    limit: NotRequired[int]
    min_similarity: NotRequired[float]
    max_revisions: NotRequired[int]

    plan_summary: NotRequired[str]
    plan: NotRequired[list[PlanStep]]
    dependencies: NotRequired[list[str]]
    risks: NotRequired[list[str]]

    evidence: NotRequired[list[PlanEvidence]]
    step_results: NotRequired[list[dict]]

    draft: NotRequired[str]
    critique: NotRequired[str]
    issues: NotRequired[list[str]]
    confidence: NotRequired[float]
    verification_passed: NotRequired[bool]

    revision_count: NotRequired[int]
    approval: NotRequired[dict]
    final_answer: NotRequired[str]
    status: NotRequired[str]


def _extract_json(
    text: str,
) -> dict | None:
    if not text:
        return None

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")

        if cleaned.lower().startswith(
            "json"
        ):
            cleaned = cleaned[4:]

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        parsed = json.loads(
            cleaned[start : end + 1]
        )

    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


def _normalise_plan(
    payload: dict | None,
    task: str,
) -> dict:
    fallback = {
        "summary": (
            "Research the task with the knowledge base "
            "and produce a grounded deliverable."
        ),
        "steps": [
            {
                "id": 1,
                "title": "Retrieve relevant evidence",
                "action": "search_knowledge",
                "query": task,
            },
            {
                "id": 2,
                "title": "Analyse dependencies and risks",
                "action": "analyze",
                "query": "",
            },
            {
                "id": 3,
                "title": "Draft the deliverable",
                "action": "draft",
                "query": "",
            },
        ],
        "dependencies": [],
        "risks": [
            "The planner response could not be parsed, "
            "so a safe generic plan was used."
        ],
    }

    if payload is None:
        return fallback

    raw_steps = payload.get("steps")

    if not isinstance(raw_steps, list):
        raw_steps = []

    steps = []

    for index, item in enumerate(
        raw_steps[:MAX_STEPS]
    ):
        if not isinstance(item, dict):
            continue

        action = str(
            item.get("action", "")
        ).strip()

        if action not in ALLOWED_ACTIONS:
            action = "analyze"

        query = str(
            item.get("query") or ""
        ).strip()

        # Some models occasionally translate the search query even when the
        # task and documents are in English. Fall back to the step title plus
        # the original task so retrieval stays on-language.
        if (
            NON_LATIN_PATTERN.search(query)
            and not NON_LATIN_PATTERN.search(task)
        ):
            query = ""

        if (
            action == "search_knowledge"
            and not query
        ):
            title = str(
                item.get("title") or ""
            ).strip()

            query = (
                f"{title}. {task}".strip(". ")
                if title
                else task
            )

        steps.append(
            {
                "id": index + 1,
                "title": str(
                    item.get("title")
                    or f"Step {index + 1}"
                ).strip(),
                "action": action,
                "query": query,
            }
        )

    if not steps:
        return fallback

    if not any(
        step["action"]
        == "search_knowledge"
        for step in steps
    ):
        steps[0] = {
            **steps[0],
            "action": "search_knowledge",
            "query": steps[0]["query"] or task,
        }

    dependencies = payload.get(
        "dependencies"
    )

    risks = payload.get("risks")

    return {
        "summary": str(
            payload.get("summary")
            or fallback["summary"]
        ).strip(),
        "steps": steps,
        "dependencies": [
            str(item)
            for item in (
                dependencies
                if isinstance(
                    dependencies,
                    list,
                )
                else []
            )
        ][:6],
        "risks": [
            str(item)
            for item in (
                risks
                if isinstance(
                    risks,
                    list,
                )
                else []
            )
        ][:6],
    }


def build_planning_graph(
    rag_service,
    llm,
    checkpointer=None,
):
    async def planner(
        state: PlanningState,
    ) -> dict:
        task = state["task"]

        prompt = f"""
TASK:

{task}

Produce the JSON plan now.
""".strip()

        try:
            raw = await llm.generate(
                system_prompt=(
                    PLANNER_SYSTEM_PROMPT
                ),
                user_prompt=prompt,
            )

        except Exception:
            raw = ""

        plan = _normalise_plan(
            _extract_json(raw),
            task,
        )

        return {
            "plan_summary": plan["summary"],
            "plan": plan["steps"],
            "dependencies": plan[
                "dependencies"
            ],
            "risks": plan["risks"],
            "evidence": [],
            "step_results": [],
            "revision_count": 0,
        }

    async def executor(
        state: PlanningState,
    ) -> dict:
        steps = state.get("plan", [])

        evidence: list[PlanEvidence] = []
        results: list[dict] = []

        seen_chunks: set[int] = set()

        for step in steps:
            if (
                step["action"]
                != "search_knowledge"
            ):
                results.append(
                    {
                        "id": step["id"],
                        "title": step["title"],
                        "action": step[
                            "action"
                        ],
                        "status": "ready",
                        "evidence_count": 0,
                    }
                )

                continue

            matches = await rag_service.retrieve(
                question=(
                    step["query"]
                    or state["task"]
                ),
                limit=state.get(
                    "limit",
                    5,
                ),
                min_similarity=state.get(
                    "min_similarity",
                    0.2,
                ),
            )

            added = 0

            for chunk, distance in matches:
                if chunk.id in seen_chunks:
                    continue

                seen_chunks.add(chunk.id)
                added += 1

                if (
                    len(evidence)
                    >= MAX_EVIDENCE_ITEMS
                ):
                    continue

                evidence.append(
                    {
                        "step_id": step["id"],
                        "document_id": (
                            chunk.document_id
                        ),
                        "position": (
                            chunk.position
                        ),
                        "similarity": round(
                            1.0 - float(distance),
                            4,
                        ),
                        "content": (
                            chunk.content[:700]
                        ),
                    }
                )

            results.append(
                {
                    "id": step["id"],
                    "title": step["title"],
                    "action": step["action"],
                    "status": (
                        "completed"
                        if matches
                        else "empty"
                    ),
                    "evidence_count": added,
                }
            )

        return {
            "evidence": evidence,
            "step_results": results,
        }

    async def synthesizer(
        state: PlanningState,
    ) -> dict:
        revision = (
            state.get("revision_count", 0)
            + 1
        )

        evidence_text = "\n\n".join(
            (
                f"[Document {item['document_id']} "
                f"- Chunk {item['position']} "
                f"- Similarity "
                f"{item['similarity']:.4f} "
                f"- plan step {item['step_id']}]\n"
                f"{item['content']}"
            )
            for item in state.get(
                "evidence",
                [],
            )
        )

        if not evidence_text:
            evidence_text = (
                "No evidence was retrieved from the "
                "knowledge base."
            )

        critique_block = ""

        if revision > 1:
            issues = "\n".join(
                f"- {issue}"
                for issue in state.get(
                    "issues",
                    [],
                )
            )

            critique_block = f"""
A previous draft was rejected by the reviewer.
Fix every issue and keep the supported parts.

REVIEWER CRITIQUE:

{state.get("critique", "")}

ISSUES:

{issues or "- No specific issues were returned."}
""".strip()

        plan_text = "\n".join(
            (
                f"{step['id']}. "
                f"{step['title']} "
                f"({step['action']})"
            )
            for step in state.get(
                "plan",
                [],
            )
        )

        prompt = f"""
TASK:

{state["task"]}

PLAN:

{plan_text}

EVIDENCE:

{evidence_text}

{critique_block}

Write the deliverable now.
""".strip()

        try:
            draft = await llm.generate(
                system_prompt=(
                    SYNTHESIZER_SYSTEM_PROMPT
                ),
                user_prompt=prompt,
            )

        except Exception as exc:
            draft = (
                "The deliverable could not be "
                "generated because the language "
                f"model failed: {exc}"
            )

        return {
            "draft": clean_model_answer(draft),
            "revision_count": revision,
        }

    async def verifier(
        state: PlanningState,
    ) -> dict:
        evidence_text = "\n\n".join(
            (
                f"[Document {item['document_id']} "
                f"- Chunk {item['position']}]\n"
                f"{item['content']}"
            )
            for item in state.get(
                "evidence",
                [],
            )
        )

        prompt = f"""
TASK:

{state["task"]}

EVIDENCE:

{evidence_text or "No evidence retrieved."}

DRAFT:

{state.get("draft", "")}

Review the draft now.
""".strip()

        try:
            raw = await llm.generate(
                system_prompt=(
                    VERIFIER_SYSTEM_PROMPT
                ),
                user_prompt=prompt,
            )

        except Exception:
            raw = ""

        review = _extract_json(raw) or {}

        evidence_count = len(
            state.get("evidence", [])
        )

        default_passed = evidence_count > 0

        passed = bool(
            review.get(
                "passed",
                default_passed,
            )
        )

        try:
            confidence = float(
                review.get("confidence", 0.5)
            )

        except (TypeError, ValueError):
            confidence = 0.5

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        issues = review.get("issues")

        if not isinstance(issues, list):
            issues = []

        critique = str(
            review.get("critique")
            or (
                "The reviewer did not return a "
                "written critique."
            )
        ).strip()

        if (
            not passed
            and not issues
        ):
            issues = [
                "The reviewer did not consider "
                "the draft fully supported by "
                "the retrieved evidence."
            ]

        return {
            "verification_passed": passed,
            "confidence": confidence,
            "issues": [
                str(issue)
                for issue in issues
            ][:8],
            "critique": critique,
        }

    def route_after_verification(
        state: PlanningState,
    ) -> str:
        if state.get(
            "verification_passed",
            False,
        ):
            return "approval"

        if (
            state.get("revision_count", 1)
            >= state.get(
                "max_revisions",
                1,
            )
        ):
            return "approval"

        return "revise"

    def approval(
        state: PlanningState,
    ) -> dict:
        decision = interrupt(
            {
                "action": "approve_plan",
                "message": (
                    "Review the research plan and "
                    "the draft before it is "
                    "released."
                ),
                "plan_summary": state.get(
                    "plan_summary",
                    "",
                ),
                "plan": state.get("plan", []),
                "draft": state.get(
                    "draft",
                    "",
                ),
                "verification_passed": (
                    state.get(
                        "verification_passed",
                        False,
                    )
                ),
                "confidence": state.get(
                    "confidence",
                    0.0,
                ),
                "issues": state.get(
                    "issues",
                    [],
                ),
                "critique": state.get(
                    "critique",
                    "",
                ),
                "revision_count": state.get(
                    "revision_count",
                    0,
                ),
            }
        )

        if isinstance(decision, dict):
            return {"approval": decision}

        return {
            "approval": {
                "approved": bool(decision)
            }
        }

    def route_after_approval(
        state: PlanningState,
    ) -> str:
        approval_state = state.get(
            "approval",
            {},
        )

        if approval_state.get(
            "approved",
            False,
        ):
            return "finalize"

        return "rejected"

    def finalize(
        state: PlanningState,
    ) -> dict:
        note = (
            state.get("approval", {})
            .get("note")
        )

        answer = state.get("draft", "")

        if note:
            answer = (
                f"{answer}\n\n"
                f"> Approved with note: {note}"
            )

        return {
            "final_answer": answer.strip(),
            "status": "completed",
        }

    def rejected(
        state: PlanningState,
    ) -> dict:
        note = (
            state.get("approval", {})
            .get("note")
        )

        message = (
            "The plan was rejected by the "
            "reviewer. Nothing was released."
        )

        if note:
            message = f"{message} Note: {note}"

        return {
            "final_answer": message,
            "status": "rejected",
        }

    builder = StateGraph(PlanningState)

    builder.add_node("planner", planner)
    builder.add_node("executor", executor)
    builder.add_node(
        "synthesizer",
        synthesizer,
    )
    builder.add_node("verifier", verifier)
    builder.add_node("approval", approval)
    builder.add_node("finalize", finalize)
    builder.add_node("rejected", rejected)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    builder.add_edge(
        "executor",
        "synthesizer",
    )
    builder.add_edge(
        "synthesizer",
        "verifier",
    )

    builder.add_conditional_edges(
        "verifier",
        route_after_verification,
        {
            "revise": "synthesizer",
            "approval": "approval",
        },
    )

    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "finalize": "finalize",
            "rejected": "rejected",
        },
    )

    builder.add_edge("finalize", END)
    builder.add_edge("rejected", END)

    return builder.compile(
        checkpointer=checkpointer
    )
