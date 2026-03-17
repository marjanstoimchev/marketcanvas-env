"""MarketCanvas-Env: A minimalist 2D design canvas as RL environment and MCP server."""

from .actions import Action, ActionType
from .canvas_engine import CanvasElement, CanvasEngine, ElementType
from .constraints import EXAMPLE_PROMPTS, TargetSpec, parse_target_prompt
from .environment import CanvasEnv, StepResult
from .mcp_server import MCPServer
from .renderer import render_canvas
from .reward import RewardBreakdown, compute_reward

__all__ = [
    "CanvasEngine",
    "CanvasElement",
    "ElementType",
    "CanvasEnv",
    "StepResult",
    "Action",
    "ActionType",
    "TargetSpec",
    "parse_target_prompt",
    "EXAMPLE_PROMPTS",
    "compute_reward",
    "RewardBreakdown",
    "render_canvas",
    "MCPServer",
]
