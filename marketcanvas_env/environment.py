"""Gymnasium-like RL environment for banner design.

Implements reset()/step()/render() without depending on gymnasium.
Episode-based: the agent gets max_steps actions to design a banner,
then receives a final reward score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .actions import Action, ActionType
from .canvas_engine import CanvasEngine, ElementType
from .constraints import EXAMPLE_PROMPTS, TargetSpec, parse_target_prompt
from .renderer import render_canvas
from .reward import RewardBreakdown, compute_reward


@dataclass
class StepResult:
    """Result of a single environment step.

    Mirrors the gymnasium (observation, reward, terminated, truncated, info) tuple.
    """

    observation: dict[str, Any]
    reward: float
    terminated: bool
    truncated: bool
    info: dict[str, Any]


class CanvasEnv:
    """Episode-based RL environment for 2D banner design.

    Usage::

        env = CanvasEnv(target_prompt="Create a banner with headline 'Hello'")
        obs = env.reset()

        for _ in range(20):
            action = {"action": "add_element", "params": {...}}
            result = env.step(action)
            if result.terminated or result.truncated:
                break

        env.render("output.png")
    """

    def __init__(
        self,
        target_prompt: str | None = None,
        max_steps: int = 20,
        canvas_width: int = 800,
        canvas_height: int = 600,
    ):
        self.engine = CanvasEngine(width=canvas_width, height=canvas_height)
        self.max_steps = max_steps
        self.current_step = 0
        self._episode_active = False
        self._action_history: list[dict[str, Any]] = []

        prompt = target_prompt or EXAMPLE_PROMPTS["summer_sale"]
        self.target = parse_target_prompt(prompt, max_steps=max_steps)

    def reset(self, target_prompt: str | None = None) -> dict[str, Any]:
        """Reset the environment for a new episode.

        Args:
            target_prompt: Optional new target prompt. If None, reuses current.

        Returns:
            Initial observation (empty canvas state + target info).
        """
        self.engine.clear()
        self.current_step = 0
        self._episode_active = True
        self._action_history = []

        if target_prompt is not None:
            self.target = parse_target_prompt(
                target_prompt, max_steps=self.max_steps
            )

        return self._get_observation()

    def step(self, action_dict: dict[str, Any]) -> StepResult:
        """Execute one action and return the result.

        Args:
            action_dict: Action in format {"action": str, "params": dict}.

        Returns:
            StepResult with observation, reward, termination flags, info.
        """
        if not self._episode_active:
            raise RuntimeError(
                "Episode not active. Call reset() to start a new episode."
            )

        info: dict[str, Any] = {"step": self.current_step}

        # Validate and parse the action
        try:
            action = Action.from_dict(action_dict)
        except (ValueError, KeyError) as e:
            self.current_step += 1
            info["error"] = str(e)
            info["action_valid"] = False
            truncated = self.current_step >= self.max_steps
            if truncated:
                self._episode_active = False
            breakdown = compute_reward(self.engine, self.target)
            return StepResult(
                observation=self._get_observation(),
                reward=max(-1.0, breakdown.total_reward - 0.05),
                terminated=False,
                truncated=truncated,
                info=info,
            )

        # Execute the action
        exec_result = self._execute_action(action)
        info["action_valid"] = exec_result["success"]
        info["action_result"] = exec_result
        self._action_history.append(action_dict)

        self.current_step += 1

        # Compute reward
        breakdown = compute_reward(self.engine, self.target)
        reward = breakdown.total_reward
        info["reward_breakdown"] = breakdown.to_dict()

        # Check termination
        truncated = self.current_step >= self.max_steps
        terminated = False

        if truncated:
            self._episode_active = False

        return StepResult(
            observation=self._get_observation(),
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            info=info,
        )

    def render(self, output_path: str | Path | None = None):
        """Render the current canvas to a PNG image.

        Returns:
            PIL.Image.Image object.
        """
        return render_canvas(self.engine, output_path)

    def get_reward_breakdown(self) -> RewardBreakdown:
        """Get detailed reward breakdown for the current state."""
        return compute_reward(self.engine, self.target)

    def _get_observation(self) -> dict[str, Any]:
        """Build the observation dictionary."""
        return {
            "canvas": self.engine.to_dict(),
            "spatial_relationships": self._compute_spatial_relationships(),
            "target": self.target.to_dict(),
            "step": self.current_step,
            "steps_remaining": self.max_steps - self.current_step,
            "episode_active": self._episode_active,
        }

    def _compute_spatial_relationships(self) -> list[dict[str, Any]]:
        """Compute pairwise spatial relationships between all elements.

        For each pair, reports overlap status, intersection area,
        relative position (above/below/left/right), and z-order.
        """
        elems = self.engine.get_elements_sorted_by_z()
        n = len(elems)
        if n < 2:
            return []

        relationships: list[dict[str, Any]] = []
        for i in range(n):
            for j in range(i + 1, n):
                a, b = elems[i], elems[j]
                bb_a = a.bounding_box()
                bb_b = b.bounding_box()

                # Intersection area
                x_overlap = max(0, min(bb_a[2], bb_b[2]) - max(bb_a[0], bb_b[0]))
                y_overlap = max(0, min(bb_a[3], bb_b[3]) - max(bb_a[1], bb_b[1]))
                overlap_area = x_overlap * y_overlap

                # Relative position (center of B relative to center of A)
                ca = a.center()
                cb = b.center()
                dx = cb[0] - ca[0]
                dy = cb[1] - ca[1]

                if abs(dx) > abs(dy):
                    rel_pos = "right" if dx > 0 else "left"
                else:
                    rel_pos = "below" if dy > 0 else "above"

                relationships.append({
                    "element_a": a.id,
                    "element_b": b.id,
                    "overlaps": overlap_area > 0,
                    "overlap_area": round(overlap_area, 1),
                    "relative_position": f"{b.id} is {rel_pos} {a.id}",
                    "z_order": f"{b.id} is above {a.id}" if b.z_index > a.z_index else f"{a.id} is above {b.id}",
                })

        return relationships

    def _execute_action(self, action: Action) -> dict[str, Any]:
        """Execute a validated action on the engine.

        Returns dict with success status and any error/element info.
        """
        try:
            p = action.params

            if action.action_type == ActionType.ADD_ELEMENT:
                elem_type_str = p["element_type"]
                try:
                    elem_type = ElementType(elem_type_str)
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Invalid element_type: '{elem_type_str}'. "
                        f"Use: {[t.value for t in ElementType]}",
                    }
                elem = self.engine.add_element(
                    element_type=elem_type,
                    x=float(p["x"]),
                    y=float(p["y"]),
                    width=float(p["width"]),
                    height=float(p["height"]),
                    color=p.get("color", "#FFFFFF"),
                    text_color=p.get("text_color", "#000000"),
                    content=p.get("content", ""),
                )
                return {"success": True, "element_id": elem.id}

            elif action.action_type == ActionType.MOVE_ELEMENT:
                elem = self.engine.move_element(
                    p["element_id"], float(p["x"]), float(p["y"])
                )
                return {"success": True, "element_id": elem.id}

            elif action.action_type == ActionType.RESIZE_ELEMENT:
                elem = self.engine.resize_element(
                    p["element_id"], float(p["width"]), float(p["height"])
                )
                return {"success": True, "element_id": elem.id}

            elif action.action_type == ActionType.CHANGE_COLOR:
                elem = self.engine.change_color(p["element_id"], p["color"])
                if p.get("text_color"):
                    self.engine.change_text_color(
                        p["element_id"], p["text_color"]
                    )
                return {"success": True, "element_id": elem.id}

            elif action.action_type == ActionType.CHANGE_TEXT:
                elem = self.engine.change_text(p["element_id"], p["content"])
                return {"success": True, "element_id": elem.id}

            elif action.action_type == ActionType.DELETE_ELEMENT:
                elem = self.engine.remove_element(p["element_id"])
                return {"success": True, "element_id": elem.id}

            elif action.action_type == ActionType.NO_OP:
                return {"success": True}

            return {"success": False, "error": "Unknown action type"}

        except (KeyError, ValueError) as e:
            return {"success": False, "error": str(e)}
