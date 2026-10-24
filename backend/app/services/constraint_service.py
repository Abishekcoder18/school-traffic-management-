"""GateFlow AI — Constraint Validation Service

Validates parsed constraints against the canonical scenario.
Acts as the hard gate between AI/parser output and the planner.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.models.schedule import ConstraintValidationResult, ParsedConstraints
from app.services.data_service import get_scenario

logger = logging.getLogger(__name__)

# Valid cohort IDs in this scenario
VALID_COHORT_IDS = {"c-prek", "c-g13", "c-g45", "c-g68", "c-hs"}
VALID_GATE_IDS = {"gate-1", "gate-2", "gate-3", "gate-4"}
VALID_OBJECTIVES = {"queue_reduction", "minimal_disruption", "balanced"}


def validate_constraints(constraints: ParsedConstraints) -> ConstraintValidationResult:
    """
    Deterministic constraint validation against the canonical scenario.
    Returns errors that will block planning, and warnings that won't.
    """
    errors: list[str] = []
    warnings: list[str] = []
    scenario = get_scenario()
    valid_cohort_ids = {c.id for c in scenario.cohorts}

    # ── Demand factor bounds ──────────────────────────────────────────────
    if constraints.demandFactor < 0.5:
        errors.append(
            f"demandFactor {constraints.demandFactor} is below 0.5. "
            "Values below 50% of baseline are outside the modeled scenario range."
        )
    if constraints.demandFactor > 2.0:
        errors.append(
            f"demandFactor {constraints.demandFactor} exceeds 2.0 (200%). "
            "The campus infrastructure cannot accommodate this demand level."
        )

    # ── Fixed groups must reference real cohort IDs ───────────────────────
    for gid in constraints.fixedGroups:
        if gid not in valid_cohort_ids:
            errors.append(
                f"Fixed group '{gid}' does not exist in the scenario. "
                f"Valid cohort IDs: {sorted(valid_cohort_ids)}"
            )

    # ── Max shift bounds ──────────────────────────────────────────────────
    if constraints.maxShiftMin < 0:
        errors.append("maxShiftMin cannot be negative.")
    if constraints.maxShiftMin > 60:
        warnings.append(
            "maxShiftMin > 60 minutes. Shifts this large may conflict with "
            "operational schedules outside this model."
        )
    if constraints.maxShiftMin == 0:
        errors.append(
            "maxShiftMin = 0 means no cohort can be rescheduled. "
            "The planner cannot improve on the baseline with this constraint."
        )

    # ── Objective must be a valid option ──────────────────────────────────
    if constraints.optimizationObjective not in VALID_OBJECTIVES:
        errors.append(
            f"Unknown optimizationObjective: '{constraints.optimizationObjective}'. "
            f"Valid: {sorted(VALID_OBJECTIVES)}"
        )

    # ── Contradiction: all cohorts fixed → no planning possible ───────────
    if set(constraints.fixedGroups) >= valid_cohort_ids:
        errors.append(
            "All cohorts are fixed. No rescheduling is possible. "
            "Remove at least one cohort from fixedGroups."
        )

    # ── Propagate prior contradiction flags ───────────────────────────────
    for flag in constraints.contradictionFlags:
        if flag not in errors:
            errors.append(flag)

    valid = len(errors) == 0
    return ConstraintValidationResult(
        valid=valid,
        constraints=constraints if valid else None,
        errors=errors,
        warnings=warnings,
        clarificationRequired=(
            " | ".join(constraints.ambiguityFlags)
            if constraints.ambiguityFlags
            else None
        ),
    )
