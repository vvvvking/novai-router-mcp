<!-- mcp-name: io.github.vvvvking/novai-router-mcp -->

# novai-router-mcp

An MCP server that answers: **for this workload, which Chinese model should I call, and what will it cost?**

It routes on **cost and workload shape** — not on quality claims. Give it a task (`coding`, `agent`, `chat`, `summarize`, `video`, `image`) and an optional budget ceiling, and it returns the cheapest models that fit, priced in a comparable unit.

## Tools

| Tool | What it does |
|---|---|
| `pick_model` | Cheapest models for a task shape (`coding` = 1M in + 200K out; `agent` = 20M in + 4M out; `video` = per 5-second clip; `image` = per image), optional `max_cost` ceiling |
| `compare_models` | Side-by-side cost for a shortlist at a given input/output volume |
| `list_categories` | Categories in the live price feed |

## Example

```
→ pick_model {"task": "coding", "max_cost": 1.0, "limit": 3}
← Cheapest options for task='coding' (per 1M in + 0.2M out):
  - GLM-4.7-Flash (Zhipu AI) — $0.0000 — free tier
  - GLM-5.3-Flash (Zhipu AI) — $0.1360
  - DeepSeek-V4-Flash (DeepSeek) — $0.1140
```

```
→ compare_models {"models": ["deepseek-v4-pro", "kimi-k2.7-code", "glm-5.3"]}
← Cost for 1,000,000 input + 200,000 output tokens:
  - DeepSeek-V4-Pro (DeepSeek): $0.8000
  - Kimi-K2.7-Code (Moonshot AI): $1.3500
  - GLM-5.3 (Zhipu AI): $2.0500
```

## Why

Every Chinese provider quotes a different unit, and agent frameworks keep re-optimising the same decision by hand. This server makes the cost side of that decision mechanical: it reads a public live price feed, converts to a common unit, and returns the shortlist.

It does **not** rank by model quality — that depends on your task, your prompts and your evals. It tells you what the cheapest options are; you decide which one is good enough.

## Setup

No dependencies beyond Python 3.9+. No API key needed (the price feed is public).

```json
{
  "mcpServers": {
    "novai-router": {
      "command": "python3",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

## Data

`https://aiapi-pro.com/china-ai-leaderboard.json` — regenerated daily, provider list price with 0% platform markup.

## License

MIT
