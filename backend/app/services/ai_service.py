"""GateFlow AI — AI Service (Deterministic-Only Mode)

In this deployment, no external AI API is called.
All constraint parsing is performed by a deterministic rule-based parser.
This is clearly labeled on every response.

If a GEMINI_API_KEY is provided in future, this module can be extended
to call Gemini — but all AI output must still pass validation before
reaching the planner.
"""
from __future__ import annotations

import logging
import re

from app.models.schedule import ConstraintValidationResult, ParsedConstraints

logger = logging.getLogger(__name__)

# Known cohort names for matching
COHORT_ALIASES = {
    "kindergarten": "c-prek",
    "pre-k": "c-prek",
    "early care": "c-prek",
    "grades 1": "c-g13",
    "grade 1": "c-g13",
    "grades 1-3": "c-g13",
    "grades 1–3": "c-g13",
    "lower elementary": "c-g13",
    "elementary lower": "c-g13",
    "grades 4": "c-g45",
    "grade 4": "c-g45",
    "grades 4-5": "c-g45",
    "grades 4–5": "c-g45",
    "upper elementary": "c-g45",
    "elementary upper": "c-g45",
    "middle school": "c-g68",
    "grades 6": "c-g68",
    "grade 6": "c-g68",
    "grades 6-8": "c-g68",
    "grades 6–8": "c-g68",
    "high school": "c-hs",
    "grades 9": "c-hs",
    "grade 9": "c-hs",
    "grades 9-12": "c-hs",
    "grades 9–12": "c-hs",
}


def _extract_demand_factor(text: str) -> float:
    """Parse 'increase/decrease demand by X%' patterns."""
    match = re.search(
        r"(increase|boost|raise|add)\s+demand\s+by\s+(\d+(?:\.\d+)?)\s*%",
        text,
        re.IGNORECASE,
    )
    if match:
        pct = float(match.group(2))
        return round(1.0 + pct / 100.0, 4)

    match = re.search(
        r"(decrease|reduce|lower|cut)\s+demand\s+by\s+(\d+(?:\.\d+)?)\s*%",
        text,
        re.IGNORECASE,
    )
    if match:
        pct = float(match.group(2))
        return round(1.0 - pct / 100.0, 4)

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*(demand|more vehicles?|extra vehicles?)",
        text,
        re.IGNORECASE,
    )
    if match:
        pct = float(match.group(1))
        return round(1.0 + pct / 100.0, 4)

    return 1.0


def _extract_fixed_groups(text: str) -> list[str]:
    """Parse 'keep X fixed / unchanged / at current time' patterns."""
    fixed = []
    patterns = [
        r"keep\s+([^,\.]+?)\s+(?:fixed|unchanged|at\s+\d)",
        r"don'?t\s+(?:move|shift|change)\s+([^,\.]+)",
        r"([^,\.]+)\s+(?:must\s+)?(?:stay|remain)\s+(?:fixed|at\s+)",
    ]
    lower = text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, lower, re.IGNORECASE):
            candidate_text = match.group(1).strip()
            for alias, cohort_id in COHORT_ALIASES.items():
                if alias in candidate_text:
                    if cohort_id not in fixed:
                        fixed.append(cohort_id)
    return fixed


def _extract_sibling_sync(text: str) -> bool:
    """Detect sibling synchronization intent."""
    sibling_keywords = [
        "sibling", "siblings", "family", "families", "multi-child",
        "synchronize", "synchronized", "sync", "together",
    ]
    lower = text.lower()
    return any(kw in lower for kw in sibling_keywords)


def _extract_max_shift(text: str) -> int:
    """Parse 'maximum X minute shift' patterns."""
    match = re.search(
        r"max(?:imum)?\s+(\d+)[- ]?min(?:ute)?(?:\s+shift)?",
        text,
        re.IGNORECASE,
    )
    if match:
        return min(60, max(5, int(match.group(1))))  # clamp 5–60 min

    match = re.search(
        r"(?:shift|move)\s+(?:by\s+)?(?:no\s+more\s+than\s+)?(\d+)\s+min",
        text,
        re.IGNORECASE,
    )
    if match:
        return min(60, max(5, int(match.group(1))))

    return 30  # default


def _extract_objective(text: str) -> str:
    """Determine the optimization objective from intent keywords."""
    lower = text.lower()
    queue_keywords = ["queue", "spillback", "bottleneck", "congestion", "throughput"]
    disruption_keywords = [
        "disruption", "disrupt", "minimal change", "least change",
        "parent", "family", "preserve", "keep current",
    ]
    if any(kw in lower for kw in queue_keywords):
        return "queue_reduction"
    if any(kw in lower for kw in disruption_keywords):
        return "minimal_disruption"
    return "balanced"


def _detect_contradictions(
    demand_factor: float,
    fixed_groups: list[str],
    max_shift: int,
) -> list[str]:
    """Check for logical contradictions in parsed constraints."""
    issues = []
    if demand_factor > 1.5:
        issues.append(
            f"Demand factor {demand_factor:.2f} exceeds 150% — "
            "most gate configurations cannot absorb this without severe spillback."
        )
    if demand_factor < 0.5:
        issues.append(
            "Demand factor below 50% is outside the modeled scenario range."
        )
    if max_shift == 0:
        issues.append(
            "A max shift of 0 minutes means no cohort can be rescheduled — "
            "the planner cannot improve on the baseline."
        )
    # If all 5 cohort IDs are fixed, nothing can change
    all_cohorts = {"c-prek", "c-g13", "c-g45", "c-g68", "c-hs"}
    if set(fixed_groups) >= all_cohorts:
        issues.append(
            "All cohorts are fixed — no rescheduling is possible. "
            "Remove at least one group from the fixed list."
        )
    return issues


def _detect_ambiguity(prompt: str, fixed_groups: list[str]) -> list[str]:
    """Flag unclear or unsupported requests."""
    flags = []
    lower = prompt.lower()
    if "bus" in lower and "schedule" not in lower:
        flags.append(
            "Bus schedule integration is referenced but not directly controllable "
            "in this planning model."
        )
    if len(prompt.split()) < 4:
        flags.append(
            "Prompt is very short — the parser may have missed constraints. "
            "Please provide more detail."
        )
    return flags


def parse_constraints_deterministic(prompt: str) -> ConstraintValidationResult:
    """
    Deterministic rule-based constraint parser.
    All output is clearly labeled as 'deterministic' parsing.
    The AI code path is intentionally omitted in this deployment.

    Pipeline:
        USER PROMPT
            ↓
        deterministic regex parser
            ↓
        structured ParsedConstraints
            ↓
        contradiction check
            ↓
        ConstraintValidationResult
    """
    errors: list[str] = []
    warnings: list[str] = []

    demand_factor = _extract_demand_factor(prompt)
    fixed_groups = _extract_fixed_groups(prompt)
    sibling_sync = _extract_sibling_sync(prompt)
    max_shift = _extract_max_shift(prompt)
    objective = _extract_objective(prompt)
    ambiguity = _detect_ambiguity(prompt, fixed_groups)
    contradictions = _detect_contradictions(demand_factor, fixed_groups, max_shift)

    if contradictions:
        errors.extend(contradictions)

    if demand_factor != 1.0:
        warnings.append(
            f"Demand will be scaled by {demand_factor:.2f}x "
            f"({round((demand_factor - 1) * 100):+d}%). "
            "This affects the synthetic baseline only."
        )

    if fixed_groups:
        warnings.append(
            f"Fixed cohorts (will not be rescheduled): "
            f"{', '.join(fixed_groups)}"
        )

    clarification = None
    if ambiguity:
        clarification = " | ".join(ambiguity)

    constraints = ParsedConstraints(
        originalPrompt=prompt,
        demandFactor=demand_factor,
        fixedGroups=fixed_groups,
        siblingSync=sibling_sync,
        maxShiftMin=max_shift,
        optimizationObjective=objective,
        ambiguityFlags=ambiguity,
        contradictionFlags=contradictions,
        parserMethod="deterministic",
    )

    valid = len(errors) == 0
    return ConstraintValidationResult(
        valid=valid,
        constraints=constraints if valid else None,
        errors=errors,
        warnings=warnings,
        clarificationRequired=clarification,
    )
