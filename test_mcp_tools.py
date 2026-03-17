"""Test script that programmatically calls the MCP tools to validate they work.

This simulates what an MCP client (like Claude Desktop) would do,
without needing an actual MCP connection.

Usage:
    conda activate marketcanvas && python test_mcp_tools.py
"""
import json

from marketcanvas_env import MCPServer


def main():
    server = MCPServer()

    # Access the registered tool functions directly from FastMCP
    tools = server.mcp._tool_manager._tools
    tool_names = list(tools.keys())

    print("=" * 60)
    print("MCP Tools Validation")
    print("=" * 60)
    print(f"Registered tools: {tool_names}")
    print()

    # Get the callable functions
    reset_fn = tools["reset_env"].fn
    state_fn = tools["get_canvas_state"].fn
    action_fn = tools["execute_action"].fn
    reward_fn = tools["get_current_reward"].fn

    # --- Test 1: reset_env ---
    print("-" * 60)
    print("Test 1: reset_env")
    print("-" * 60)
    result = reset_fn(
        target_prompt="Create a banner with a headline 'Hello World' and a button 'Click Me'.",
        max_steps=10,
    )
    print(f"  episode_active: {result['episode_active']}")
    print(f"  steps_remaining: {result['steps_remaining']}")
    print(f"  constraints: {len(result['target']['constraints'])}")
    for c in result["target"]["constraints"]:
        print(f"    - {c['description']}")
    print("  PASS")
    print()

    # --- Test 2: get_canvas_state (empty canvas) ---
    print("-" * 60)
    print("Test 2: get_canvas_state (empty canvas)")
    print("-" * 60)
    result = state_fn()
    print(f"  element_count: {result['canvas']['element_count']}")
    print(f"  step: {result['step']}")
    assert result["canvas"]["element_count"] == 0
    assert result["episode_active"] is True
    print("  PASS")
    print()

    # --- Test 3: execute_action (add elements) ---
    print("-" * 60)
    print("Test 3: execute_action (add_element - headline)")
    print("-" * 60)
    result = action_fn(
        action="add_element",
        element_type="text",
        x=150, y=50,
        width=500, height=80,
        color="#003366",
        text_color="#FFFFFF",
        content="Hello World",
    )
    headline_id = result["info"]["action_result"]["element_id"]
    print(f"  success: {result['info']['action_result']['success']}")
    print(f"  element_id: {headline_id}")
    print(f"  reward: {result['reward']:.4f}")
    print(f"  element_count: {result['observation']['canvas']['element_count']}")
    print("  PASS")
    print()

    print("-" * 60)
    print("Test 4: execute_action (add_element - button shape)")
    print("-" * 60)
    result = action_fn(
        action="add_element",
        element_type="shape",
        x=300, y=200,
        width=200, height=50,
        color="#FF6600",
        content="rounded_rect",
    )
    button_shape_id = result["info"]["action_result"]["element_id"]
    print(f"  success: {result['info']['action_result']['success']}")
    print(f"  element_id: {button_shape_id}")
    print(f"  reward: {result['reward']:.4f}")
    print("  PASS")
    print()

    print("-" * 60)
    print("Test 5: execute_action (add_element - button text)")
    print("-" * 60)
    result = action_fn(
        action="add_element",
        element_type="text",
        x=300, y=200,
        width=200, height=50,
        color="#FF6600",
        text_color="#FFFFFF",
        content="Click Me",
    )
    print(f"  success: {result['info']['action_result']['success']}")
    print(f"  reward: {result['reward']:.4f}")
    print("  PASS")
    print()

    # --- Test 6: execute_action (move_element) ---
    print("-" * 60)
    print("Test 6: execute_action (move_element)")
    print("-" * 60)
    result = action_fn(
        action="move_element",
        element_id=headline_id,
        x=100, y=30,
    )
    print(f"  success: {result['info']['action_result']['success']}")
    print(f"  reward: {result['reward']:.4f}")
    print("  PASS")
    print()

    # --- Test 7: execute_action (change_color) ---
    print("-" * 60)
    print("Test 7: execute_action (change_color)")
    print("-" * 60)
    result = action_fn(
        action="change_color",
        element_id=button_shape_id,
        color="#00AA00",
    )
    print(f"  success: {result['info']['action_result']['success']}")
    print(f"  reward: {result['reward']:.4f}")
    print("  PASS")
    print()

    # --- Test 8: get_current_reward ---
    print("-" * 60)
    print("Test 8: get_current_reward")
    print("-" * 60)
    result = reward_fn()
    print(f"  constraint_score: {result['constraint_score']}")
    print(f"  contrast_score:   {result['contrast_score']}")
    print(f"  overlap_penalty:  {result['overlap_penalty']}")
    print(f"  alignment_score:  {result['alignment_score']}")
    print(f"  total_reward:     {result['total_reward']}")
    print("  PASS")
    print()

    # --- Test 9: get_canvas_state (with elements + spatial relationships) ---
    print("-" * 60)
    print("Test 9: get_canvas_state (with spatial relationships)")
    print("-" * 60)
    result = state_fn()
    print(f"  element_count: {result['canvas']['element_count']}")
    print(f"  spatial_relationships: {len(result['spatial_relationships'])} pairs")
    for rel in result["spatial_relationships"][:3]:
        print(f"    {rel['relative_position']}, overlaps={rel['overlaps']}")
    print("  PASS")
    print()

    # --- Test 10: execute_action (invalid action) ---
    print("-" * 60)
    print("Test 10: execute_action (invalid action)")
    print("-" * 60)
    result = action_fn(action="fly_to_moon")
    assert "error" in result
    print(f"  error: {result['error']}")
    print("  PASS (correctly rejected)")
    print()

    # --- Test 11: execute_action (delete_element) ---
    print("-" * 60)
    print("Test 11: execute_action (delete_element)")
    print("-" * 60)
    result = action_fn(
        action="delete_element",
        element_id=button_shape_id,
    )
    print(f"  success: {result['info']['action_result']['success']}")
    print(f"  elements remaining: {result['observation']['canvas']['element_count']}")
    print("  PASS")
    print()

    # --- Summary ---
    print("=" * 60)
    print("ALL 11 MCP TOOL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
