"""Action space definitions for the MarketCanvas RL environment.

Defines the high-level semantic actions an agent can take to
manipulate the canvas: adding, moving, resizing, recoloring,
editing, and deleting elements.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionType(Enum):
    """High-level semantic actions available to the agent."""

    ADD_ELEMENT = "add_element"
    MOVE_ELEMENT = "move_element"
    RESIZE_ELEMENT = "resize_element"
    CHANGE_COLOR = "change_color"
    CHANGE_TEXT = "change_text"
    DELETE_ELEMENT = "delete_element"
    NO_OP = "no_op"


# Parameter schemas: required keys, optional keys with defaults, and types.
ACTION_PARAM_SCHEMAS: dict[str, dict[str, Any]] = {
    "add_element": {
        "required": ["element_type", "x", "y", "width", "height"],
        "optional": {
            "color": "#FFFFFF",
            "text_color": "#000000",
            "content": "",
        },
    },
    "move_element": {
        "required": ["element_id", "x", "y"],
        "optional": {},
    },
    "resize_element": {
        "required": ["element_id", "width", "height"],
        "optional": {},
    },
    "change_color": {
        "required": ["element_id", "color"],
        "optional": {"text_color": None},
    },
    "change_text": {
        "required": ["element_id", "content"],
        "optional": {},
    },
    "delete_element": {
        "required": ["element_id"],
        "optional": {},
    },
    "no_op": {
        "required": [],
        "optional": {},
    },
}


@dataclass
class Action:
    """A validated action to be executed on the canvas.

    Attributes:
        action_type: The type of action.
        params: Dictionary of action parameters.
    """

    action_type: ActionType
    params: dict[str, Any]

    @classmethod
    def from_dict(cls, action_dict: dict[str, Any]) -> Action:
        """Parse and validate an action from a raw dictionary.

        Expected format:
            {"action": "add_element", "params": {"element_type": "text", ...}}
        """
        action_name = action_dict.get("action", "")
        params = action_dict.get("params", {})

        # Validate action type
        try:
            action_type = ActionType(action_name)
        except ValueError:
            raise ValueError(
                f"Unknown action '{action_name}'. "
                f"Valid actions: {[a.value for a in ActionType]}"
            )

        # Validate required params
        schema = ACTION_PARAM_SCHEMAS.get(action_name, {})
        for key in schema.get("required", []):
            if key not in params:
                raise ValueError(
                    f"Action '{action_name}' requires parameter '{key}'"
                )

        # Fill in optional defaults
        for key, default in schema.get("optional", {}).items():
            if key not in params and default is not None:
                params[key] = default

        return cls(action_type=action_type, params=params)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {"action": self.action_type.value, "params": self.params}


def validate_action(action_dict: dict[str, Any]) -> tuple[bool, str]:
    """Validate an action dictionary without constructing an Action.

    Returns:
        (is_valid, error_message) -- error_message is "" if valid.
    """
    try:
        Action.from_dict(action_dict)
        return (True, "")
    except (ValueError, KeyError) as e:
        return (False, str(e))
