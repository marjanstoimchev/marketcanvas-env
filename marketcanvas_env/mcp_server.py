"""FastMCP server exposing the MarketCanvas environment as tools.

Allows LLM clients (like Claude Desktop) to interact with the canvas
environment via standard MCP tool calling.

Usage:
    python run_mcp_server.py
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .constraints import EXAMPLE_PROMPTS
from .environment import CanvasEnv


class MCPServer:
    """Wraps CanvasEnv and exposes it via FastMCP tools.

    Tools:
        - get_canvas_state: Returns current canvas observation
        - execute_action: Executes a design action
        - get_current_reward: Returns detailed reward breakdown
        - reset_env: Resets environment with optional new prompt
    """

    def __init__(
        self,
        name: str = "MarketCanvas-Env",
        target_prompt: str | None = None,
        max_steps: int = 20,
    ):
        self.env = CanvasEnv(target_prompt=target_prompt, max_steps=max_steps)
        self.mcp = FastMCP(name=name)
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all MCP tools."""

        @self.mcp.tool(
            name="get_canvas_state",
            description=(
                "Get the current canvas state including all elements, "
                "target constraints, step count, and steps remaining. "
                "Returns a JSON object with canvas dimensions, element list "
                "(sorted by z-index), and episode metadata."
            ),
        )
        def get_canvas_state() -> dict[str, Any]:
            if not self.env._episode_active:
                return {
                    "error": "No active episode. Call reset_env first.",
                    "episode_active": False,
                }
            return self.env._get_observation()

        @self.mcp.tool(
            name="execute_action",
            description=(
                "Execute a design action on the canvas. "
                "Actions: add_element, move_element, resize_element, "
                "change_color, change_text, delete_element, no_op.\n\n"
                "For add_element: provide element_type ('text','shape','image'), "
                "x, y, width, height, color, text_color, content.\n"
                "For move_element: provide element_id, x, y.\n"
                "For resize_element: provide element_id, width, height.\n"
                "For change_color: provide element_id, color, optionally text_color.\n"
                "For change_text: provide element_id, content.\n"
                "For delete_element: provide element_id.\n"
                "Returns observation, reward, terminated, truncated, and info."
            ),
        )
        def execute_action(
            action: str,
            element_type: str = "",
            element_id: str = "",
            x: float = 0.0,
            y: float = 0.0,
            width: float = 100.0,
            height: float = 50.0,
            color: str = "#FFFFFF",
            text_color: str = "#000000",
            content: str = "",
        ) -> dict[str, Any]:
            # Build action dict from flat params
            params: dict[str, Any] = {}
            if action == "add_element":
                params = {
                    "element_type": element_type,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "color": color,
                    "text_color": text_color,
                    "content": content,
                }
            elif action == "move_element":
                params = {"element_id": element_id, "x": x, "y": y}
            elif action == "resize_element":
                params = {
                    "element_id": element_id,
                    "width": width,
                    "height": height,
                }
            elif action == "change_color":
                params = {
                    "element_id": element_id,
                    "color": color,
                    "text_color": text_color,
                }
            elif action == "change_text":
                params = {"element_id": element_id, "content": content}
            elif action == "delete_element":
                params = {"element_id": element_id}
            elif action == "no_op":
                params = {}
            else:
                return {
                    "error": f"Unknown action '{action}'. Valid: "
                    "add_element, move_element, resize_element, "
                    "change_color, change_text, delete_element, no_op"
                }

            action_dict = {"action": action, "params": params}
            result = self.env.step(action_dict)
            return {
                "observation": result.observation,
                "reward": result.reward,
                "terminated": result.terminated,
                "truncated": result.truncated,
                "info": result.info,
            }

        @self.mcp.tool(
            name="get_current_reward",
            description=(
                "Get a detailed breakdown of the current reward score "
                "without consuming a step. Returns constraint satisfaction, "
                "WCAG contrast score, overlap penalty, alignment score, "
                "and total reward."
            ),
        )
        def get_current_reward() -> dict[str, Any]:
            breakdown = self.env.get_reward_breakdown()
            return breakdown.to_dict()

        @self.mcp.tool(
            name="reset_env",
            description=(
                "Reset the environment to start a new design episode. "
                "Optionally provide a target_prompt describing what the "
                "banner should contain. If empty, uses the default "
                "'Summer Sale' prompt. Returns the initial observation."
            ),
        )
        def reset_env(
            target_prompt: str = "",
            max_steps: int = 20,
        ) -> dict[str, Any]:
            prompt = target_prompt if target_prompt else None
            self.env.max_steps = max_steps
            obs = self.env.reset(target_prompt=prompt)
            return obs

        @self.mcp.tool(
            name="render_canvas",
            description=(
                "Render the current canvas state to a PNG file. "
                "Provide an output_path where the image should be saved. "
                "Returns the file path on success."
            ),
        )
        def render_canvas_tool(
            output_path: str = "figures/canvas_output.png",
        ) -> dict[str, Any]:
            try:
                self.env.render(output_path)
                return {"success": True, "output_path": output_path}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def run(self, transport: str = "stdio") -> None:
        """Start the MCP server."""
        self.mcp.run(transport=transport)
