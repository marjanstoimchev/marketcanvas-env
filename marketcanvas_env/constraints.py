"""Target prompt parsing into structured design constraints.

Converts natural language prompts like:
  "Create a banner with a headline 'Summer Sale', a subtitle '50% Off',
   and a call-to-action button 'Shop Now'. Use a blue background."

into a list of Constraint objects that the reward function evaluates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConstraintType(Enum):
    """Types of design constraints derived from target prompts."""

    REQUIRED_ELEMENT = "required_element"
    REQUIRED_TEXT = "required_text"
    BACKGROUND_COLOR = "background_color"
    MIN_ELEMENTS = "min_elements"
    MAX_ELEMENTS = "max_elements"


@dataclass
class Constraint:
    """A single design constraint.

    Attributes:
        type: The constraint category.
        params: Constraint-specific parameters.
        weight: Relative importance for reward calculation.
        description: Human-readable description.
    """

    type: ConstraintType
    params: dict[str, Any]
    weight: float = 1.0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "params": self.params,
            "weight": self.weight,
            "description": self.description,
        }


@dataclass
class TargetSpec:
    """A fully parsed target specification for one episode.

    Attributes:
        raw_prompt: The original prompt string.
        constraints: List of parsed constraints.
        max_steps: Maximum steps allowed for this episode.
    """

    raw_prompt: str
    constraints: list[Constraint] = field(default_factory=list)
    max_steps: int = 20

    def total_weight(self) -> float:
        return sum(c.weight for c in self.constraints)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.raw_prompt,
            "constraints": [c.to_dict() for c in self.constraints],
            "max_steps": self.max_steps,
        }


# Color keywords mapped to hex values for background detection
_COLOR_KEYWORDS: dict[str, str] = {
    "blue": "#0066CC",
    "red": "#CC0000",
    "green": "#00AA00",
    "yellow": "#FFDD00",
    "orange": "#FF8800",
    "purple": "#8800CC",
    "black": "#000000",
    "white": "#FFFFFF",
    "dark": "#333333",
    "pink": "#FF69B4",
}

# Keywords that indicate specific roles for quoted text
_HEADLINE_KEYWORDS = {"headline", "title", "heading", "header"}
_SUBTITLE_KEYWORDS = {"subtitle", "subheading", "sub-heading", "subhead", "tagline"}
_BUTTON_KEYWORDS = {"button", "cta", "call-to-action", "call to action"}


def _classify_by_nearest_keyword(context: str) -> str:
    """Find the closest role keyword in context (nearest to the end = closest to quote).

    Uses word-boundary regex to avoid matching 'title' inside 'subtitle'.
    Returns one of: 'headline', 'subtitle', 'button', 'generic'.
    """
    best_role = "generic"
    best_pos = -1

    all_keywords = (
        [("subtitle", kw) for kw in _SUBTITLE_KEYWORDS]
        + [("headline", kw) for kw in _HEADLINE_KEYWORDS]
        + [("button", kw) for kw in _BUTTON_KEYWORDS]
    )

    for role, kw in all_keywords:
        # Use word-boundary search to avoid substring matches
        for m in re.finditer(r"\b" + re.escape(kw) + r"\b", context):
            if m.start() > best_pos:
                best_pos = m.start()
                best_role = role

    return best_role


def parse_target_prompt(prompt: str, max_steps: int = 20) -> TargetSpec:
    """Parse a natural language target prompt into a TargetSpec.

    Uses rule-based keyword extraction to identify required elements,
    text content, background colors, and structural constraints.
    """
    spec = TargetSpec(raw_prompt=prompt, max_steps=max_steps)
    lower_prompt = prompt.lower()

    # Step 1: Extract all quoted strings with their positions
    quoted_matches = list(re.finditer(r"""['"]([^'"]+)['"]""", prompt))

    for match in quoted_matches:
        text = match.group(1)
        pos = match.start()

        # Get ~50 chars before the quote for context
        context = prompt[max(0, pos - 50) : pos].lower()

        # Find the closest keyword to the quote to avoid misclassification
        role = _classify_by_nearest_keyword(context)

        if role == "headline":
            spec.constraints.append(
                Constraint(
                    type=ConstraintType.REQUIRED_TEXT,
                    params={"text": text, "role": "headline"},
                    weight=2.0,
                    description=f"Must contain headline: '{text}'",
                )
            )
        elif role == "subtitle":
            spec.constraints.append(
                Constraint(
                    type=ConstraintType.REQUIRED_TEXT,
                    params={"text": text, "role": "subtitle"},
                    weight=1.5,
                    description=f"Must contain subtitle: '{text}'",
                )
            )
        elif role == "button":
            spec.constraints.append(
                Constraint(
                    type=ConstraintType.REQUIRED_TEXT,
                    params={"text": text, "role": "button"},
                    weight=1.5,
                    description=f"Must contain button text: '{text}'",
                )
            )
        else:
            spec.constraints.append(
                Constraint(
                    type=ConstraintType.REQUIRED_TEXT,
                    params={"text": text, "role": "generic"},
                    weight=1.0,
                    description=f"Must contain text: '{text}'",
                )
            )

    # Step 2: Check for background color
    for color_name, hex_value in _COLOR_KEYWORDS.items():
        if f"{color_name} background" in lower_prompt:
            spec.constraints.append(
                Constraint(
                    type=ConstraintType.BACKGROUND_COLOR,
                    params={"color": hex_value, "color_name": color_name},
                    weight=1.0,
                    description=f"Background should be {color_name}",
                )
            )
            break  # Only one background color

    # Step 3: Check for required element types
    if any(kw in lower_prompt for kw in ["image", "photo", "picture", "logo"]):
        spec.constraints.append(
            Constraint(
                type=ConstraintType.REQUIRED_ELEMENT,
                params={"element_type": "image"},
                weight=1.0,
                description="Must contain an image element",
            )
        )

    if any(kw in lower_prompt for kw in ["button", "cta"]):
        spec.constraints.append(
            Constraint(
                type=ConstraintType.REQUIRED_ELEMENT,
                params={"element_type": "shape"},
                weight=0.5,
                description="Must contain a shape element (for button)",
            )
        )

    # Step 4: Add default structural constraints
    spec.constraints.append(
        Constraint(
            type=ConstraintType.MIN_ELEMENTS,
            params={"count": 2},
            weight=0.5,
            description="At least 2 elements",
        )
    )
    spec.constraints.append(
        Constraint(
            type=ConstraintType.MAX_ELEMENTS,
            params={"count": 10},
            weight=0.5,
            description="At most 10 elements",
        )
    )

    return spec


# Pre-built target prompts for common banner scenarios
EXAMPLE_PROMPTS: dict[str, str] = {
    "summer_sale": (
        "Create a banner with a headline 'Summer Sale', "
        "a subtitle '50% Off Everything', "
        "and a call-to-action button 'Shop Now'. "
        "Use a blue background."
    ),
    "product_launch": (
        "Design a banner with a title 'New Product', "
        "a subtitle 'Available Now', "
        "an image placeholder, "
        "and a button 'Learn More'."
    ),
    "simple_announcement": (
        "Create a simple banner with a headline 'Welcome' "
        "and a subtitle 'Check out our latest updates'."
    ),
}
