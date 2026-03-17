# MarketCanvas-Env: Design Writeup

## Setup

```bash
# 1. Create and activate a conda environment (Python 3.11+)
conda create -n marketcanvas python=3.11 -y
conda activate marketcanvas

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the demo (designs a "Summer Sale" banner, saves figures/demo_output.png)
python demo.py

# 4. Run the test suite (validates all MCP tools)
python test_mcp_tools.py

# 5. Start the MCP server standalone (listens on stdio)
python run_mcp_server.py
```

## Project Structure

```
marketcanvas_env/           # Core package
├── __init__.py             # Public exports
├── color_utils.py          # Hex/RGB conversion, WCAG luminance & contrast ratio
├── canvas_engine.py        # CanvasElement dataclass + CanvasEngine CRUD
├── actions.py              # ActionType enum + parameter schemas + validation
├── constraints.py          # Prompt parser: natural language → design constraints
├── reward.py               # 4-component heuristic reward function
├── renderer.py             # Pillow-based PNG rendering
├── environment.py          # CanvasEnv: Gymnasium-like reset()/step()/render()
└── mcp_server.py           # FastMCP server wrapping CanvasEnv as 5 tools
demo.py                     # Scripted demo: builds a banner, prints rewards, saves PNG
test_mcp_tools.py           # 11-test validation of all MCP tools
run_mcp_server.py           # MCP server CLI entry point
requirements.txt            # Dependencies: mcp, Pillow
start_mcp.sh                # Conda wrapper for MCP server startup
.mcp.json                   # MCP config for Claude Code (optional)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│                                                                 │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐   │
│   │  Claude Code  │   │ Claude       │   │  demo.py /       │   │
│   │  (via MCP)    │   │ Desktop      │   │  custom script   │   │
│   └──────┬───────┘   └──────┬───────┘   └────────┬─────────┘   │
│          │                  │                     │             │
└──────────┼──────────────────┼─────────────────────┼─────────────┘
           │ MCP (stdio)      │ MCP (stdio)         │ Python API
           ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Server Layer                            │
│                                                                 │
│   mcp_server.py → FastMCP with 5 tools:                        │
│   ┌────────────┐ ┌───────────────┐ ┌──────────────────┐        │
│   │ reset_env  │ │ execute_action│ │ get_canvas_state │        │
│   └────────────┘ └───────────────┘ └──────────────────┘        │
│   ┌──────────────────┐ ┌───────────────┐                       │
│   │ get_current_reward│ │ render_canvas │                       │
│   └──────────────────┘ └───────────────┘                       │
│                                                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Environment Layer                             │
│                                                                 │
│   environment.py → CanvasEnv                                    │
│   ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐     │
│   │ reset()  │  │  step()  │  │ get_reward_breakdown()   │     │
│   └──────────┘  └──────────┘  └──────────────────────────┘     │
│                                                                 │
│   Episode: reset → step → step → ... → terminated/truncated    │
│                                                                 │
└──────┬──────────────┬───────────────┬───────────────┬───────────┘
       │              │               │               │
       ▼              ▼               ▼               ▼
┌────────────┐ ┌────────────┐ ┌─────────────┐ ┌────────────┐
│  Canvas    │ │  Actions   │ │   Reward    │ │  Renderer  │
│  Engine    │ │            │ │   Function  │ │            │
│            │ │ 7 action   │ │             │ │  Pillow    │
│ Elements   │ │ types with │ │ 4 components│ │  PNG       │
│ CRUD ops   │ │ validation │ │ clipped to  │ │  rendering │
│ 800x600    │ │            │ │ [-1, 1]     │ │            │
├────────────┤ ├────────────┤ ├─────────────┤ ├────────────┤
│canvas_     │ │actions.py  │ │reward.py    │ │renderer.py │
│engine.py   │ │            │ │             │ │            │
└────────────┘ └────────────┘ └──────┬──────┘ └────────────┘
                                     │
                              ┌──────┴──────┐
                              ▼             ▼
                       ┌────────────┐ ┌────────────┐
                       │ Constraints│ │ Color      │
                       │            │ │ Utils      │
                       │ NLP prompt │ │            │
                       │ → design   │ │ WCAG       │
                       │ constraints│ │ contrast   │
                       ├────────────┤ ├────────────┤
                       │constraints │ │color_      │
                       │.py         │ │utils.py    │
                       └────────────┘ └────────────┘
```

**Data flow for a single step:**

```
Client prompt                    "Add blue background"
       │
       ▼
MCP Server                       Parses into action dict
       │
       ▼
CanvasEnv.step()                  Validates action
       │
       ├──► CanvasEngine          Adds/modifies element
       ├──► Reward Function       Scores canvas (constraints + contrast + overlap + alignment)
       └──► Observation           Returns JSON state + reward + done flag
              │
              ▼
Client receives                   Decides next action based on reward
```

## MCP Server

The MCP server exposes 5 tools via the Model Context Protocol:

| Tool | Description |
|------|-------------|
| `reset_env` | Start a new episode with a target prompt and max steps. Returns initial observation. |
| `get_canvas_state` | Get current canvas state: elements, spatial relationships, constraints, step count. |
| `execute_action` | Execute a design action (add/move/resize/recolor/retext/delete/no_op). Returns observation, reward, terminated, truncated, info. |
| `get_current_reward` | Get detailed reward breakdown without consuming a step. |
| `render_canvas` | Render the current canvas to a PNG file. |

**Standalone usage** (no Claude needed):

```bash
# Start server on stdio
python run_mcp_server.py

# Or with a custom prompt
python run_mcp_server.py --prompt "Create a holiday sale banner" --max-steps 15
```

Any MCP-compatible client can connect to the server over stdio transport.

### Optional: Connecting to Claude Code

To let Claude interact with the canvas directly via tool-calling:

**1.** The `.mcp.json` config is already included in the project root:

```json
{
  "mcpServers": {
    "marketcanvas": {
      "command": "bash",
      "args": ["./start_mcp.sh"]
    }
  }
}
```

**2.** Edit `start_mcp.sh` to match your conda installation:

```bash
#!/bin/bash
CONDA_PATH="$HOME/anaconda3"           # <-- adjust if needed (e.g. miniconda3)
source "$CONDA_PATH/etc/profile.d/conda.sh"
conda activate marketcanvas
cd "$(dirname "$0")"
exec python run_mcp_server.py
```

**3.** Open Claude Code in the project directory and run `/mcp`. You should see `marketcanvas` with 5 tools listed.

**4. Using it** — once connected, prompt Claude to design a banner. Example session:

```
You: Design a Summer Sale banner with a headline "50% Off Everything",
     a subtitle "Limited Time Only", and a "Shop Now" button on a blue background.
```

Claude will then autonomously:
1. Call `reset_env` with the target prompt to start an episode
2. Call `execute_action` repeatedly to add elements (background, headline, subtitle, button)
3. Call `get_current_reward` to check the score and adjust the design
4. Call `render_canvas` to save the final result as a PNG

Each action returns the current reward so Claude can iteratively improve the layout. A well-designed banner typically scores > 0.6.

**Disconnect** — to disable the MCP connection without deleting the config, run `/mcp` in Claude Code and remove the `marketcanvas` server.

**Cleanup** — to fully remove:

```bash
rm .mcp.json                          # Remove MCP config
conda deactivate
conda env remove -n marketcanvas -y   # Remove conda environment
```

## 1. State Space Design

The observation is a **structured JSON dictionary** (semantic state) rather than a pixel array:

```json
{
  "canvas": {"width": 800, "height": 600, "elements": [...]},
  "spatial_relationships": [
    {"element_a": "abc", "element_b": "def", "overlaps": false,
     "overlap_area": 0, "relative_position": "def is below abc",
     "z_order": "def is above abc"}
  ],
  "target": {"prompt": "...", "constraints": [...]},
  "step": 3,
  "steps_remaining": 17
}
```

**Rationale**: The primary consumers are LLM-based agents that natively process structured text. A pixel-based observation would require a CNN/ViT encoder and would discard the precise element metadata (IDs, types, exact coordinates) that the agent needs to reference when issuing subsequent actions. The JSON representation provides **information-complete** state — every property of every element is directly accessible — while a pixel rendering is lossy (you can't read exact hex colors or element IDs from pixels).

The observation includes an explicit **spatial relationships** field that computes pairwise relationships between all elements. For each pair, it reports: whether they overlap, the intersection area in pixels, the relative position (above/below/left/right based on center-point comparison), and z-order stacking. This serves as an accessibility-tree-like representation that lets the agent reason about layout without computing geometry itself — critical for LLM agents that struggle with spatial arithmetic.

For multimodal (VLM) training, we also provide `render()` which produces an 800x600 RGB pixel array via Pillow. This can be used alongside the semantic state for vision-language model training, but the semantic state remains the primary observation for efficiency.

The state also includes the **target specification** (prompt + parsed constraints), giving the agent full information about what it needs to achieve. This is equivalent to providing the task description as part of the observation in goal-conditioned RL.

## 2. Action Space Design

We chose a **high-level semantic action space** with 7 action types:

| Action | Parameters | Purpose |
|--------|-----------|---------|
| `add_element` | type, x, y, w, h, color, text_color, content | Create new canvas element |
| `move_element` | element_id, x, y | Reposition an element |
| `resize_element` | element_id, w, h | Change element dimensions |
| `change_color` | element_id, color, text_color | Modify colors |
| `change_text` | element_id, content | Edit text content |
| `delete_element` | element_id | Remove an element |
| `no_op` | (none) | Skip a step |

**Why semantic over low-level (mouse/keyboard)?**

1. **Combinatorial explosion**: A low-level action space of `mouse_move(x,y)` on an 800x600 canvas has 480,000 position choices per step. Combined with click/drag/type, the effective action space is unbounded. Our semantic space has ~7 discrete action types with bounded continuous parameters.

2. **LLM alignment**: LLMs naturally express design intent as "add a blue rectangle at position (100, 200)" rather than "move mouse to (100, 200), click, drag to (300, 400), release." The semantic space maps directly to how an MCP tool-calling agent operates.

3. **Reward attribution**: With semantic actions, each step makes a meaningful canvas change, making it straightforward to attribute reward to specific actions. Low-level actions require many steps for a single logical operation, creating severe credit assignment problems.

**Trade-off**: The semantic action space assumes a well-defined element model. It cannot represent arbitrary freeform operations (e.g., gradient fills, arbitrary path drawing). For a production Canva clone, we'd need a richer primitive set, but for banner design RL, this is sufficient.

## 3. Reward Function

The reward is an **additive heuristic** computed from four components, clipped to [-1.0, 1.0]:

```
reward = clip(
    constraint_satisfaction × 0.4  +
    wcag_contrast          × 0.2  +
    (−overlap_penalty)     × 0.2  +
    alignment_score        × 0.2,
    −1.0, 1.0
)
```

### Components

**Constraint Satisfaction (40%)**: The largest weight because it captures the primary objective — did the agent build what was requested? Each constraint (required headline, subtitle, button, background color) is checked and scored. Partial credit is given for substring matches (0.5) vs exact matches (1.0). Constraints are weighted by importance (headline=2.0, subtitle=1.5, button=1.5, structural=0.5).

**WCAG Contrast (20%)**: For each text element, we compute the WCAG 2.1 contrast ratio between text color and background color. Ratios ≥ 4.5 score 1.0 (AA pass), ≥ 3.0 score 0.5 (large text only), < 3.0 score 0.0. This incentivizes readable text without being overly prescriptive about color choices.

**Overlap Penalty (20%, subtracted)**: Pairwise IoU (Intersection over Union) is computed for all element pairs. IoU > 0.1 contributes to the penalty. This discourages illegible element stacking. We explicitly exempt: (a) full-canvas background shapes (IoU with small elements is naturally low anyway), and (b) "button pattern" pairs (a shape and text element at the same position forming a button).

**Alignment Score (20%)**: Three sub-components: horizontal centering (are elements centered on the canvas?), vertical distribution (are vertical gaps between elements even?), and edge margins (do elements maintain ≥10px from canvas edges?). This rewards visually balanced layouts.

### Potential Reward Hacking

1. **Text duplication**: An agent could add the same required text multiple times to boost the constraint score. Mitigation: the constraint check uses `best_match` — duplicates don't increase the score beyond 1.0 per constraint.

2. **Contrast gaming**: Setting all text to white-on-black (contrast ratio 21:1) trivially maxes the contrast score regardless of aesthetic quality. Mitigation: contrast is only 20% of the total reward, so gaming it alone yields at most 0.2.

3. **Alignment exploitation**: Stacking all elements at the exact canvas center with identical sizes would maximize centering and distribution scores. Mitigation: the overlap penalty counterbalances this.

4. **Minimal compliance**: Adding exactly the required elements with no effort on layout. This achieves ~0.4 (constraints) but loses on alignment and aesthetics. The 60% quality weight ensures minimal-effort designs score poorly.

5. **Background color loophole**: The background color constraint checks for full-canvas shapes, so any large blue rectangle satisfies "blue background" even if the actual `background_color` property is white. This is by design (the visual result is correct), but a stricter implementation could require the engine property to match.

## 4. Scaling to 10,000 Parallel Rollouts with a VLM

### Bottleneck Analysis

Running PPO with 10K parallel environments using a Vision-Language Model creates bottlenecks at several layers:

**1. VLM Inference Latency (Primary Bottleneck)**: A VLM forward pass (e.g., rendering → image encoding → text generation → action sampling) takes 50-500ms on a modern GPU. With 10K environments generating observations simultaneously, naive sequential inference would take 500K seconds per environment step. Even with batching, the GPU memory required for 10K image contexts (800×600×3 = 1.44MB each, ~14GB just for raw pixels) limits batch sizes.

**2. Environment Rendering**: Pillow's CPU-based rendering at 800×600 is ~2ms per frame. For 10K environments, that's 20 seconds per step if sequential. This is manageable with multiprocessing but becomes significant at scale.

**3. Reward Computation**: Our heuristic reward is O(n²) in element count (pairwise overlap). With typical banner designs (5-10 elements), this is negligible (~0.1ms). At scale, it's not a bottleneck.

**4. Communication Overhead**: Serializing/deserializing 10K JSON observations and pixel arrays between environment workers and the inference server adds latency, especially if environments and GPUs are on different machines.

### Redesign Strategy

**A. Decouple Environment Workers from Inference**

Separate the architecture into:
- **Environment Worker Pool** (CPU): 10K lightweight Python processes, each running a `CanvasEnv`. These can run on CPU-only machines. Use `multiprocessing` or Ray for orchestration.
- **Inference Server** (GPU): A batch inference service (e.g., vLLM, TensorRT-LLM) that accepts batches of observations and returns batched action distributions. The key insight is that inference is the bottleneck, so we should maximize GPU utilization by batching.

**B. Use Semantic State by Default, Pixel State on Demand**

For most training steps, use the JSON semantic state as input to the language model component. Render pixels only for the vision component, and do so lazily (render only when the VLM requests visual verification). This reduces CPU rendering load by 10-100x during exploration phases.

**C. Vectorized Environment with Shared Memory**

Instead of 10K separate processes, use a vectorized environment (`AsyncVectorEnv` pattern) where:
- Canvas states are stored in shared memory (NumPy arrays in shared buffers)
- A single process manages all 10K canvases with batch operations
- Rendering is done in parallel with a thread pool or GPU-based renderer (e.g., using OpenGL/Vulkan for batch rendering)

**D. GPU-Accelerated Rendering**

Replace Pillow with a GPU-based renderer:
- **Approach 1**: Use PyTorch to render rectangles and text as tensor operations directly on GPU, avoiding CPU-GPU transfer entirely.
- **Approach 2**: Use a headless OpenGL context (via EGL) for parallel rendering.
- This eliminates the CPU rendering bottleneck entirely.

**E. Async Rollout Collection**

Use an async architecture where:
1. Environments that are ready send observations to an inference queue
2. The inference server processes observations in optimal batch sizes (e.g., 256)
3. Actions are sent back to environments asynchronously
4. Environments don't block waiting for other environments to finish

This maximizes GPU utilization (always processing a full batch) even when environments have variable step times.

**F. Reward Model Scaling**

If we graduate from heuristic rewards to a learned reward model (e.g., a fine-tuned VLM that scores designs), the reward model itself becomes a bottleneck. Solution: train a lightweight CNN reward proxy (~10ms inference) distilled from the VLM reward model, and use it for the majority of training steps. Periodically recalibrate against the full VLM reward.

### Estimated Infrastructure

For 10K parallel PPO rollouts with a VLM:
- **GPU**: 8-16× A100/H100 GPUs for inference (batched), 1-2 for reward model
- **CPU**: 100-200 CPU cores for environment workers
- **Memory**: ~50GB for environment states, ~200GB GPU memory for model + batched inference
- **Throughput target**: ~1000 environment steps/second aggregate (0.1 steps/sec per env)
