"""Demo script: Initialize environment, run design actions, print state + reward.

Creates a 'Summer Sale' email banner step by step, printing the reward
after each action and rendering the final result to PNG.

Usage:
    conda activate marketcanvas && python demo.py
"""
import json

from marketcanvas_env import CanvasEnv


def main():
    # 1. Initialize environment with target prompt
    env = CanvasEnv(
        target_prompt=(
            "Create a banner with a headline 'Summer Sale', "
            "a subtitle '50% Off Everything', "
            "and a call-to-action button 'Shop Now'. "
            "Use a blue background."
        ),
        max_steps=20,
    )

    # 2. Reset to start the episode
    obs = env.reset()
    print("=" * 60)
    print("MarketCanvas-Env Demo")
    print("=" * 60)
    print(f"Canvas: {obs['canvas']['width']}x{obs['canvas']['height']}")
    print(f"Target: {obs['target']['prompt'][:80]}...")
    print(f"Constraints ({len(obs['target']['constraints'])}):")
    for c in obs["target"]["constraints"]:
        print(f"  - {c['description']} (weight={c['weight']})")
    print()

    # 3. Execute a sequence of design actions
    actions = [
        # Step 1: Blue background (full-canvas rectangle)
        {
            "action": "add_element",
            "params": {
                "element_type": "shape",
                "x": 0, "y": 0,
                "width": 800, "height": 600,
                "color": "#1E90FF",
                "content": "rectangle",
            },
        },
        # Step 2: Headline text
        {
            "action": "add_element",
            "params": {
                "element_type": "text",
                "x": 150, "y": 80,
                "width": 500, "height": 90,
                "color": "#1E90FF",
                "text_color": "#FFFFFF",
                "content": "Summer Sale",
            },
        },
        # Step 3: Subtitle text
        {
            "action": "add_element",
            "params": {
                "element_type": "text",
                "x": 175, "y": 210,
                "width": 450, "height": 60,
                "color": "#1E90FF",
                "text_color": "#FFFFFF",
                "content": "50% Off Everything",
            },
        },
        # Step 4: CTA button (rounded rectangle)
        {
            "action": "add_element",
            "params": {
                "element_type": "shape",
                "x": 275, "y": 340,
                "width": 250, "height": 65,
                "color": "#FF6600",
                "content": "rounded_rect",
            },
        },
        # Step 5: CTA button text
        {
            "action": "add_element",
            "params": {
                "element_type": "text",
                "x": 275, "y": 340,
                "width": 250, "height": 65,
                "color": "#FF6600",
                "text_color": "#FFFFFF",
                "content": "Shop Now",
            },
        },
        # Step 6: Decorative element (optional flourish)
        {
            "action": "add_element",
            "params": {
                "element_type": "shape",
                "x": 300, "y": 470,
                "width": 200, "height": 10,
                "color": "#FFFFFF",
                "content": "rectangle",
            },
        },
    ]

    print("-" * 60)
    print("Executing design actions:")
    print("-" * 60)
    for i, action in enumerate(actions):
        result = env.step(action)
        status = "OK" if result.info.get("action_result", {}).get("success") else "ERR"
        elem_id = result.info.get("action_result", {}).get("element_id", "")
        content = action["params"].get("content", "")
        print(
            f"  Step {i + 1}: {action['action']:15s} "
            f"{action['params'].get('element_type', ''):6s} "
            f"[{status}] id={elem_id:8s} "
            f"content='{content}'"
            f"  -> reward={result.reward:.4f}"
        )

    # 4. Print final state
    print()
    print("-" * 60)
    print("Final Canvas State:")
    print("-" * 60)
    final_obs = env._get_observation()
    print(f"  Elements: {final_obs['canvas']['element_count']}")
    for elem in final_obs["canvas"]["elements"]:
        print(
            f"    [{elem['type']:5s}] {elem['id']:8s} "
            f"at ({elem['x']:>5.0f},{elem['y']:>5.0f}) "
            f"{elem['width']:>3.0f}x{elem['height']:<3.0f} "
            f"z={elem['z_index']} "
            f"color={elem['color']} "
            f"content='{elem['content']}'"
        )

    # 5. Print reward breakdown
    print()
    print("-" * 60)
    print("Reward Breakdown:")
    print("-" * 60)
    breakdown = env.get_reward_breakdown()
    print(f"  Constraint satisfaction : {breakdown.constraint_score:.4f}  (x0.4 = {breakdown.constraint_score * 0.4:.4f})")
    print(f"  WCAG contrast score     : {breakdown.contrast_score:.4f}  (x0.2 = {breakdown.contrast_score * 0.2:.4f})")
    print(f"  Overlap penalty         : {breakdown.overlap_penalty:.4f}  (x-0.2 = {-breakdown.overlap_penalty * 0.2:.4f})")
    print(f"  Alignment score         : {breakdown.alignment_score:.4f}  (x0.2 = {breakdown.alignment_score * 0.2:.4f})")
    print(f"  {'─' * 40}")
    print(f"  TOTAL REWARD            : {breakdown.total_reward:.4f}")

    # 6. Print detailed reward info
    print()
    print("-" * 60)
    print("Reward Details:")
    print("-" * 60)
    details = breakdown.details
    if "constraints" in details:
        print("  Constraints:")
        for c in details["constraints"].get("per_constraint", []):
            mark = "PASS" if c["satisfied"] else "FAIL"
            print(f"    [{mark}] {c['description']} (score={c['score']})")
    if "contrast" in details:
        print("  Contrast:")
        for c in details["contrast"]:
            if "message" in c:
                print(f"    {c['message']}")
            else:
                mark = "PASS" if c["passed"] else "FAIL"
                print(
                    f"    [{mark}] '{c['content']}' "
                    f"ratio={c['contrast_ratio']} "
                    f"({c['text_color']} on {c['bg_color']})"
                )
    if "alignment" in details:
        print("  Alignment:")
        a = details["alignment"]
        print(f"    centering={a['centering']}, distribution={a['distribution']}, margin={a['margin']}")

    # 7. Render to PNG
    output_path = "figures/demo_output.png"
    env.render(output_path)
    print()
    print(f"Canvas rendered to: {output_path}")

    # 8. Print full JSON state (compact)
    print()
    print("-" * 60)
    print("Full JSON Observation (for MCP/RL consumption):")
    print("-" * 60)
    print(json.dumps(final_obs, indent=2)[:2000])


if __name__ == "__main__":
    main()
