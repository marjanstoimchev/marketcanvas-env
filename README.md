# MarketCanvas-Env

[![Tests](https://github.com/marjanstoimchev/marketcanvas-env/actions/workflows/tests.yml/badge.svg)](https://github.com/marjanstoimchev/marketcanvas-env/actions/workflows/tests.yml)

A minimalist 2D design canvas that serves as both a **Gymnasium-like RL environment** and an **MCP server**, enabling LLM agents to design marketing banners via tool-calling with a heuristic reward function scoring the result.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Client Layer                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Claude Code │  │Claude Desktop│  │ demo.py / scripts  │  │
│  └──────┬──────┘  └──────┬───────┘  └─────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼──────────────┘
          │ MCP (stdio)    │ MCP (stdio)        │ Python API
          ▼                ▼                    ▼
┌──────────────────────────────────────────────────────────────┐
│  MCP Server  ─  5 tools: reset_env, execute_action,         │
│  get_canvas_state, get_current_reward, render_canvas         │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  CanvasEnv  ─  reset() / step() / render()                   │
│  Episode: reset → step → step → ... → done                  │
└───────┬──────────┬──────────┬──────────┬─────────────────────┘
        ▼          ▼          ▼          ▼
   CanvasEngine  Actions   Reward    Renderer
   (CRUD ops)   (7 types)  (4-part)  (Pillow PNG)
        │                     │
        ▼                     ▼
   color_utils          constraints
   (WCAG contrast)    (NLP prompt parser)
```

## Quick Start

```bash
# Create environment
conda create -n marketcanvas python=3.11 -y
conda activate marketcanvas
pip install -r requirements.txt

# Run demo (builds a "Summer Sale" banner, saves demo_output.png)
python demo.py

# Run tests (validates all 11 MCP tool scenarios)
python test_mcp_tools.py
```

## How It Works

1. **Target prompt** is parsed into design constraints (required elements, colors, text)
2. **Agent** (LLM or script) takes actions: `add_element`, `move_element`, `resize_element`, `change_color`, `change_text`, `delete_element`, `no_op`
3. **Reward function** scores the canvas after each step:

| Component | Weight | What it measures |
|-----------|--------|------------------|
| Constraint satisfaction | 40% | Are required elements/text present? |
| WCAG contrast | 20% | Is text readable (contrast ratio >= 4.5)? |
| Overlap penalty | -20% | Are elements stacked illegibly? |
| Alignment | 20% | Are elements centered, evenly spaced, with margins? |

4. **Episode ends** when max steps reached. Total reward is clipped to [-1.0, 1.0].

## MCP Server

Start the server for any MCP-compatible client:

```bash
python run_mcp_server.py
```

| Tool | Description |
|------|-------------|
| `reset_env` | Start a new episode with a target prompt |
| `execute_action` | Execute a design action on the canvas |
| `get_canvas_state` | Get current canvas state + spatial relationships |
| `get_current_reward` | Get reward breakdown without consuming a step |
| `render_canvas` | Save canvas as PNG |

### Using with Claude Code (Optional)

The `.mcp.json` config is included. To connect:

1. Edit `start_mcp.sh` — set `CONDA_PATH` to your conda installation
2. Open Claude Code in the project directory, run `/mcp` to enable
3. Ask Claude to design a banner:

```
Design a Summer Sale banner with headline "50% Off Everything",
subtitle "Limited Time Only", and a "Shop Now" button on a blue background.
```

Claude will autonomously call the MCP tools to build the banner, check rewards, and render the result.

## Project Structure

```
marketcanvas_env/
├── __init__.py          # Public exports
├── color_utils.py       # WCAG luminance & contrast ratio
├── canvas_engine.py     # CanvasElement + CanvasEngine CRUD
├── actions.py           # 7 action types + validation
├── constraints.py       # NLP prompt → design constraints
├── reward.py            # 4-component heuristic reward
├── renderer.py          # Pillow PNG rendering
├── environment.py       # CanvasEnv (Gymnasium-like interface)
└── mcp_server.py        # FastMCP server (5 tools)
demo.py                  # Scripted demo
test_mcp_tools.py        # 11-test validation suite
run_mcp_server.py        # MCP server entry point
requirements.txt         # mcp, Pillow
start_mcp.sh             # Conda wrapper for MCP startup
.mcp.json                # Claude Code MCP config
```

## Design Writeup

See [WRITEUP.md](WRITEUP.md) for detailed design rationale covering:
- State space design (JSON semantic state vs pixel arrays)
- Action space design (semantic vs low-level actions)
- Reward function (component weights, potential reward hacking)
- Scaling analysis (10K parallel PPO rollouts with a VLM)
