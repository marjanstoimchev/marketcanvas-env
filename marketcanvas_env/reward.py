"""Heuristic reward function for banner design evaluation.

Computes a scalar reward in [-1.0, 1.0] from four additive components:

    reward = clip(
        constraint_satisfaction * 0.4 +
        wcag_contrast_score    * 0.2 +
        overlap_penalty        * (-0.2) +
        alignment_score        * 0.2,
        -1.0, 1.0
    )

Each sub-score is in [0.0, 1.0].
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .canvas_engine import CanvasEngine, CanvasElement, ElementType
from .color_utils import contrast_ratio, hex_to_rgb
from .constraints import ConstraintType, TargetSpec


@dataclass
class RewardBreakdown:
    """Detailed breakdown of the reward computation."""

    constraint_score: float = 0.0
    contrast_score: float = 0.0
    overlap_penalty: float = 0.0
    alignment_score: float = 0.0
    total_reward: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_score": round(self.constraint_score, 4),
            "contrast_score": round(self.contrast_score, 4),
            "overlap_penalty": round(self.overlap_penalty, 4),
            "alignment_score": round(self.alignment_score, 4),
            "total_reward": round(self.total_reward, 4),
            "details": self.details,
        }


def compute_reward(engine: CanvasEngine, target: TargetSpec) -> RewardBreakdown:
    """Compute the full reward for the current canvas state."""
    breakdown = RewardBreakdown()

    c_score, c_details = _compute_constraint_satisfaction(engine, target)
    breakdown.constraint_score = c_score
    breakdown.details["constraints"] = c_details

    w_score, w_details = _compute_contrast_score(engine)
    breakdown.contrast_score = w_score
    breakdown.details["contrast"] = w_details

    o_penalty, o_details = _compute_overlap_penalty(engine)
    breakdown.overlap_penalty = o_penalty
    breakdown.details["overlap"] = o_details

    a_score, a_details = _compute_alignment_score(engine)
    breakdown.alignment_score = a_score
    breakdown.details["alignment"] = a_details

    total = (
        breakdown.constraint_score * 0.4
        + breakdown.contrast_score * 0.2
        + (-breakdown.overlap_penalty) * 0.2
        + breakdown.alignment_score * 0.2
    )
    breakdown.total_reward = max(-1.0, min(1.0, total))

    return breakdown


# ---------------------------------------------------------------------------
# Sub-component 1: Constraint Satisfaction
# ---------------------------------------------------------------------------


def _compute_constraint_satisfaction(
    engine: CanvasEngine, target: TargetSpec
) -> tuple[float, dict[str, Any]]:
    """Evaluate what fraction of target constraints are satisfied."""
    if not target.constraints:
        return 1.0, {"message": "No constraints defined"}

    weighted_sum = 0.0
    total_weight = 0.0
    results: list[dict[str, Any]] = []

    for constraint in target.constraints:
        total_weight += constraint.weight
        score = 0.0

        if constraint.type == ConstraintType.REQUIRED_ELEMENT:
            target_type = constraint.params["element_type"]
            found = any(
                e.type.value == target_type
                for e in engine.elements.values()
            )
            score = 1.0 if found else 0.0

        elif constraint.type == ConstraintType.REQUIRED_TEXT:
            target_text = constraint.params["text"].lower()
            best_match = 0.0
            for e in engine.elements.values():
                if e.type == ElementType.TEXT:
                    e_content = e.content.lower()
                    if target_text == e_content:
                        best_match = 1.0
                        break
                    elif target_text in e_content or e_content in target_text:
                        best_match = max(best_match, 0.5)
            score = best_match

        elif constraint.type == ConstraintType.BACKGROUND_COLOR:
            target_color = constraint.params["color"].lower()
            # Check engine background directly
            match = engine.background_color.lower() == target_color
            # Also check for full-canvas shape acting as background
            if not match:
                for e in engine.elements.values():
                    if (
                        e.type == ElementType.SHAPE
                        and e.x <= 0
                        and e.y <= 0
                        and e.width >= engine.width
                        and e.height >= engine.height
                        and e.color.lower() == target_color
                    ):
                        match = True
                        break
            # Partial credit: check if any large shape has a similar blue
            if not match and "color_name" in constraint.params:
                color_name = constraint.params["color_name"]
                for e in engine.elements.values():
                    if (
                        e.type == ElementType.SHAPE
                        and e.width >= engine.width * 0.9
                        and e.height >= engine.height * 0.9
                    ):
                        # Check if the color is in the right family
                        try:
                            tr, tg, tb = hex_to_rgb(target_color)
                            er, eg, eb = hex_to_rgb(e.color)
                            # Simple heuristic: dominant channel match
                            if _color_family_match(
                                (tr, tg, tb), (er, eg, eb), color_name
                            ):
                                match = True
                                break
                        except ValueError:
                            pass
            score = 1.0 if match else 0.0

        elif constraint.type == ConstraintType.MIN_ELEMENTS:
            required = constraint.params["count"]
            actual = engine.element_count()
            score = min(1.0, actual / max(1, required))

        elif constraint.type == ConstraintType.MAX_ELEMENTS:
            max_count = constraint.params["count"]
            score = 1.0 if engine.element_count() <= max_count else 0.0

        weighted_sum += constraint.weight * score
        results.append(
            {
                "description": constraint.description,
                "satisfied": score >= 1.0,
                "score": round(score, 3),
            }
        )

    final_score = weighted_sum / max(total_weight, 1e-6)
    return final_score, {"per_constraint": results, "score": round(final_score, 4)}


def _color_family_match(
    target_rgb: tuple[int, int, int],
    actual_rgb: tuple[int, int, int],
    color_name: str,
) -> bool:
    """Check if actual_rgb is in the same color family as the target."""
    r, g, b = actual_rgb
    if color_name == "blue":
        return b > r and b > g and b > 80
    elif color_name == "red":
        return r > g and r > b and r > 80
    elif color_name == "green":
        return g > r and g > b and g > 80
    elif color_name == "yellow":
        return r > 150 and g > 150 and b < 100
    elif color_name == "orange":
        return r > 150 and g > 50 and b < 100
    elif color_name == "purple":
        return r > 50 and b > 50 and g < max(r, b)
    elif color_name in ("black", "dark"):
        return r < 100 and g < 100 and b < 100
    elif color_name == "white":
        return r > 200 and g > 200 and b > 200
    return False


# ---------------------------------------------------------------------------
# Sub-component 2: WCAG Contrast
# ---------------------------------------------------------------------------


def _compute_contrast_score(
    engine: CanvasEngine,
) -> tuple[float, list[dict[str, Any]]]:
    """Evaluate WCAG contrast compliance across all text elements."""
    text_elements = [
        e for e in engine.elements.values() if e.type == ElementType.TEXT
    ]

    if not text_elements:
        return 1.0, [{"message": "No text elements to check"}]

    score_sum = 0.0
    details: list[dict[str, Any]] = []

    for elem in text_elements:
        try:
            fg = hex_to_rgb(elem.text_color)
            bg = hex_to_rgb(elem.color)
        except ValueError:
            score_sum += 0.0
            details.append(
                {"element_id": elem.id, "error": "Invalid color values"}
            )
            continue

        ratio = contrast_ratio(fg, bg)

        if ratio >= 4.5:
            elem_score = 1.0  # WCAG AA normal text
        elif ratio >= 3.0:
            elem_score = 0.5  # WCAG AA large text only
        else:
            elem_score = 0.0  # Fail

        score_sum += elem_score
        details.append(
            {
                "element_id": elem.id,
                "content": elem.content[:30],
                "text_color": elem.text_color,
                "bg_color": elem.color,
                "contrast_ratio": round(ratio, 2),
                "passed": elem_score >= 1.0,
            }
        )

    return score_sum / len(text_elements), details


# ---------------------------------------------------------------------------
# Sub-component 3: Overlap Penalty
# ---------------------------------------------------------------------------


def _is_background_element(elem: CanvasElement, engine: CanvasEngine) -> bool:
    """Check if an element is a full-canvas background."""
    return (
        elem.width >= engine.width * 0.95
        and elem.height >= engine.height * 0.95
    )


def _is_button_pair(
    a: CanvasElement, b: CanvasElement
) -> bool:
    """Check if two elements form a button (shape + text at same position)."""
    types = {a.type, b.type}
    if types != {ElementType.SHAPE, ElementType.TEXT}:
        return False
    # Same bounding box within 5px tolerance
    return (
        abs(a.x - b.x) <= 5
        and abs(a.y - b.y) <= 5
        and abs(a.width - b.width) <= 5
        and abs(a.height - b.height) <= 5
    )


def _compute_overlap_penalty(
    engine: CanvasEngine,
) -> tuple[float, list[dict[str, Any]]]:
    """Compute penalty for overlapping elements.

    Uses IoU (Intersection over Union) with a 0.1 threshold.
    Exempts full-canvas backgrounds and button-pattern pairs.
    """
    elems = list(engine.elements.values())
    n = len(elems)

    if n <= 1:
        return 0.0, []

    total_iou = 0.0
    counted_pairs = 0
    details: list[dict[str, Any]] = []

    for i in range(n):
        for j in range(i + 1, n):
            a, b = elems[i], elems[j]

            # Skip background-vs-content pairs
            if _is_background_element(a, engine) or _is_background_element(
                b, engine
            ):
                continue

            # Skip button-pattern pairs (shape + text at same position)
            if _is_button_pair(a, b):
                continue

            bb_a = a.bounding_box()
            bb_b = b.bounding_box()

            x_overlap = max(0, min(bb_a[2], bb_b[2]) - max(bb_a[0], bb_b[0]))
            y_overlap = max(0, min(bb_a[3], bb_b[3]) - max(bb_a[1], bb_b[1]))
            intersection = x_overlap * y_overlap

            if intersection <= 0:
                continue

            area_a = a.width * a.height
            area_b = b.width * b.height
            union = area_a + area_b - intersection

            if union <= 0:
                continue

            iou = intersection / union
            if iou > 0.1:
                total_iou += iou
                details.append(
                    {
                        "element_a": a.id,
                        "element_b": b.id,
                        "iou": round(iou, 3),
                    }
                )
            counted_pairs += 1

    penalty = min(1.0, total_iou / max(1, counted_pairs)) if counted_pairs > 0 else 0.0
    return penalty, details


# ---------------------------------------------------------------------------
# Sub-component 4: Alignment Score
# ---------------------------------------------------------------------------


def _compute_alignment_score(
    engine: CanvasEngine,
) -> tuple[float, dict[str, Any]]:
    """Evaluate alignment and centering quality.

    Three sub-components equally weighted:
    1. Horizontal centering
    2. Vertical distribution evenness
    3. Edge margin compliance
    """
    elems = list(engine.elements.values())
    # Filter out full-canvas background shapes for alignment scoring
    content_elems = [
        e for e in elems if not _is_background_element(e, engine)
    ]
    n = len(content_elems)

    if n == 0:
        return 0.0, {"centering": 0.0, "distribution": 0.0, "margin": 0.0}

    canvas_cx = engine.width / 2.0

    # Sub-component A: Horizontal centering
    dist_sum = 0.0
    for e in content_elems:
        cx = e.x + e.width / 2.0
        dist_sum += abs(cx - canvas_cx) / canvas_cx
    centering = 1.0 - min(1.0, dist_sum / n)

    # Sub-component B: Vertical distribution
    if n < 2:
        distribution = 0.5
    else:
        sorted_by_y = sorted(content_elems, key=lambda e: e.y)
        gaps = []
        for k in range(1, len(sorted_by_y)):
            gap = sorted_by_y[k].y - (
                sorted_by_y[k - 1].y + sorted_by_y[k - 1].height
            )
            gaps.append(max(0, gap))

        mean_gap = sum(gaps) / len(gaps) if gaps else 0
        if mean_gap > 0:
            variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            std_gap = math.sqrt(variance)
            cov = std_gap / mean_gap
            if cov < 0.3:
                distribution = 1.0
            elif cov < 0.6:
                distribution = 0.5
            else:
                distribution = 0.0
        else:
            distribution = 0.0  # All overlapping or stacked

    # Sub-component C: Edge margins (10px minimum)
    margin = 10
    good_count = 0
    for e in content_elems:
        if (
            e.x >= margin
            and e.y >= margin
            and e.x + e.width <= engine.width - margin
            and e.y + e.height <= engine.height - margin
        ):
            good_count += 1
    margin_score = good_count / n

    alignment = (centering + distribution + margin_score) / 3.0

    return alignment, {
        "centering": round(centering, 4),
        "distribution": round(distribution, 4),
        "margin": round(margin_score, 4),
    }
