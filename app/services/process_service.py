import json
import re

from app.services.retrieval_service import search_knowledge_base
from app.services.llm_service import generate_answer


def _parse_json_response(response):
    """Extract a JSON object from an LLM response."""
    if isinstance(response, dict):
        return response

    if not isinstance(response, str):
        raise ValueError("The LLM returned an unsupported response type.")

    text = response.strip()

    # Handle responses wrapped in a Markdown JSON code block.
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "The LLM did not return a valid JSON worksheet."
        ) from exc


def generate_work_process(question: str) -> dict:
    """
    Generate a worksheet using retrieved knowledge-base passages.

    The API layer stores the generated explanation and ordered steps for progress tracking.
    """
    question = question.strip()

    if not question:
        raise ValueError("Please enter a work-related question.")

    # Search beyond the first few vector hits because the raw and curated
    # folders can contain repeated copies of the same pages.
    results = search_knowledge_base(query=question, k=30)

    context_parts = []
    sources = []
    seen_content = set()

    for result in results:
        content = str(result.get("content", "")).strip()

        if not content:
            continue

        content_key = " ".join(content.lower().split())
        if content_key in seen_content:
            continue
        seen_content.add(content_key)

        source = str(result.get("source") or "Unknown document")
        page = result.get("page")

        reference = source
        if page is not None:
            reference += f", page {page}"

        context_parts.append(
            f"[SOURCE: {reference}]\n{content}"
        )

        if reference not in sources:
            sources.append(reference)

        if len(context_parts) >= 10:
            break

    if not context_parts:
        return {
            "question": question,
            "status": "insufficient_information",
            "title": "Worksheet unavailable",
            "description": (
                "No relevant procedure was retrieved from the knowledge base."
            ),
            "prerequisites": [],
            "safety_notes": [],
            "steps": [],
            "sources": [],
        }

    context = "\n\n".join(context_parts)

    worksheet_prompt = f"""
Create an employee work-process worksheet for this request:

{question}

Return ONLY a valid JSON object with exactly this structure:
The status must be one of: "ready", "needs_review", or "insufficient_information".

{{
  "status": "ready",
  "title": "Short work-process title",
  "description": "Brief description of the work",
  "prerequisites": [
    "A prerequisite explicitly supported by the documents"
  ],
  "safety_notes": [
    "A safety requirement explicitly supported by the documents"
  ],
  "steps": [
    {{
      "step_number": 1,
      "title": "Step title",
      "description": "Complete, specific instruction with all supported sub-actions and sequence details",
      "source": "Document name and page, if available"
    }}
  ]
}}

Rules:
1. Use ONLY the supplied document context.
2. Do NOT invent missing steps, tools, safety requirements, or approvals.
3. Preserve the sequence specified by the source procedure.
4. Do NOT summarize or shorten the procedure. Include every distinct action and sub-step that the source describes, in its original order. Do not omit checks, conditions, hand-offs, or completion criteria.
5. Keep each step focused on one action, but split a source instruction into multiple ordered steps when it contains distinct actions. Do not add unsupported detail to make a step longer.
6. Do NOT combine conflicting procedures into one set of instructions.
7. Include a source reference for every step.
8. Choose status "ready" only when the context supports a complete,
   applicable procedure. If it supports some safe steps but does not
   establish the complete sequence, return "needs_review", include only
   the supported steps, and explain what remains unclear in "description".
   Do not turn gaps into instructions.
9. Use "insufficient_information" only when none of the retrieved passages
   support an applicable step. In that case return:
   {{
     "status": "insufficient_information",
     "title": "Worksheet unavailable",
     "description": "The retrieved documents do not contain a complete, applicable procedure.",
     "prerequisites": [],
     "safety_notes": [],
     "steps": []
   }}
10. Return JSON only. Do not include Markdown or explanatory text.
""".strip()

    # Reuse your existing LLM integration.
    response = generate_answer(
        question=worksheet_prompt,
        context=context,
        direct=True,
    )

    worksheet = _parse_json_response(response)

    if worksheet.get("status") not in {
        "ready",
        "needs_review",
        "insufficient_information",
    }:
        raise ValueError("The worksheet has an invalid status.")

    steps = worksheet.get("steps")

    if not isinstance(steps, list):
        raise ValueError("The worksheet steps must be a list.")

    if worksheet["status"] in {"ready", "needs_review"} and not steps:
        raise ValueError("A generated process must contain at least one grounded step.")

    for expected_number, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError("Each worksheet step must be an object.")

        if step.get("step_number") != expected_number:
            raise ValueError(
                "Worksheet steps must be numbered consecutively from 1."
            )

        for field in ("title", "description", "source"):
            if not isinstance(step.get(field), str) or not step[field].strip():
                raise ValueError(
                    f"Step {expected_number} is missing a valid {field}."
                )

        if step["source"] not in sources:
            raise ValueError(
                f"Step {expected_number} references an unknown source."
            )

    worksheet["question"] = question
    worksheet["sources"] = sources

    return worksheet
