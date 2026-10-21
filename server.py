#!/usr/bin/env python3
"""NovAI router MCP server (stdio, zero dependencies).

Picks a Chinese model by *cost* for a workload shape, and compares a shortlist.

Tools:
  - pick_model(task, max_cost?, limit?)     -> cheapest models for a task shape
  - compare_models(models, input_tokens, output_tokens) -> side-by-side cost
  - list_categories()
Data: https://aiapi-pro.com/china-ai-leaderboard.json
"""
import json
import sys
import urllib.request

FEED = "https://aiapi-pro.com/china-ai-leaderboard.json"
_cache = {"data": None}


def feed():
    if _cache["data"] is None:
        req = urllib.request.Request(FEED, headers={"User-Agent": "novai-router-mcp/0.1"})
        with urllib.request.urlopen(req, timeout=20) as r:
            _cache["data"] = json.load(r)
    return _cache["data"]


def models():
    return [m for c in feed().get("categories", []) for m in c.get("models", [])]


def text_cost(m, in_tok, out_tok):
    pi, po = m.get("price_per_1m_input"), m.get("price_per_1m_output")
    if pi is None:
        return None
    return pi * in_tok / 1e6 + (po or 0) * out_tok / 1e6


def pick(args):
    task = (args.get("task") or "").lower()
    max_cost = args.get("max_cost")
    limit = int(args.get("limit") or 5)
    # task -> (category hint, input tokens, output tokens)
    shapes = {
        "coding": ("chat", 1_000_000, 200_000),
        "chat": ("chat", 1_000_000, 200_000),
        "agent": ("chat", 20_000_000, 4_000_000),
        "summarize": ("chat", 2_000_000, 100_000),
        "video": ("video", 0, 0),
        "image": ("image", 0, 0),
    }
    cat, itok, otok = shapes.get(task, ("chat", 1_000_000, 200_000))
    rows = []
    for m in models():
        mc = (m.get("category") or "").lower()
        if cat not in mc:
            continue
        if cat == "video":
            cost = m.get("cost_per_5s_est")
            unit = "per 5s clip"
        elif cat == "image":
            cost = m.get("price_per_image")
            unit = "per image"
        else:
            cost = text_cost(m, itok, otok)
            unit = f"per {itok/1e6:.0f}M in + {otok/1e6:.1f}M out"
        if cost is None:
            continue
        if max_cost is not None and cost > float(max_cost):
            continue
        rows.append((cost, unit, m))
    rows.sort(key=lambda r: r[0])
    if not rows:
        return f"No model matched task='{task}'" + (f" under ${max_cost}" if max_cost else "") + "."
    out = [f"Cheapest options for task='{task}' ({rows[0][1]}):"]
    for cost, unit, m in rows[:limit]:
        out.append(f"- {m['name']} ({m.get('provider','')}) — ${cost:.4f} {unit} — {m.get('url','')}")
    out.append(f"\nFeed: {FEED}")
    return "\n".join(out)


def compare(args):
    wanted = [w.lower().strip() for w in (args.get("models") or []) if w.strip()]
    itok = int(args.get("input_tokens") or 1_000_000)
    otok = int(args.get("output_tokens") or 200_000)
    if not wanted:
        return "Pass models: [\"deepseek-v4-flash\", \"glm-5.3\"]"
    allm = models()
    out = [f"Cost for {itok:,} input + {otok:,} output tokens:"]
    for w in wanted:
        hits = [m for m in allm if w in (m.get("name") or "").lower()]
        if not hits:
            out.append(f"- {w}: not found")
            continue
        # prefer an exact / prefix match over a substring match
        def rank(m):
            n = (m.get("name") or "").lower()
            exact = 0 if n == w else (1 if n.startswith(w) else 2)
            return (exact, text_cost(m, itok, otok) if text_cost(m, itok, otok) is not None else 1e9)
        m = sorted(hits, key=rank)[0]
        c = text_cost(m, itok, otok)
        if c is None:
            out.append(f"- {m['name']}: no token pricing in feed")
        else:
            out.append(f"- {m['name']} ({m.get('provider','')}): ${c:.4f}")
    return "\n".join(out)


def categories(_args):
    return "Categories:\n" + "\n".join(f"- {c['category']} ({len(c.get('models', []))})"
                                       for c in feed().get("categories", []))


TOOLS = [
    {"name": "pick_model",
     "description": "Pick the cheapest Chinese model for a task shape (coding, agent, summarize, video, image), optionally under a cost ceiling.",
     "inputSchema": {"type": "object", "properties": {
         "task": {"type": "string", "enum": ["coding", "agent", "chat", "summarize", "video", "image"]},
         "max_cost": {"type": "number", "description": "USD ceiling for the task shape"},
         "limit": {"type": "integer"}}}},
    {"name": "compare_models",
     "description": "Compare the cost of specific models for a given input/output token volume.",
     "inputSchema": {"type": "object", "properties": {
         "models": {"type": "array", "items": {"type": "string"}},
         "input_tokens": {"type": "integer"},
         "output_tokens": {"type": "integer"}}, "required": ["models"]}},
    {"name": "list_categories",
     "description": "List model categories in the price feed.",
     "inputSchema": {"type": "object", "properties": {}}},
]

H = {"pick_model": pick, "compare_models": compare, "list_categories": categories}


def reply(mid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": mid}
    msg["error" if error is not None else "result"] = error if error is not None else result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        mid, method, params = req.get("id"), req.get("method"), req.get("params") or {}
        if method == "initialize":
            reply(mid, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                        "serverInfo": {"name": "novai-router", "version": "0.1.0"}})
        elif method == "tools/list":
            reply(mid, {"tools": TOOLS})
        elif method == "tools/call":
            fn = H.get(params.get("name"))
            if not fn:
                reply(mid, error={"code": -32601, "message": "unknown tool"})
                continue
            try:
                reply(mid, {"content": [{"type": "text", "text": fn(params.get("arguments") or {})}], "isError": False})
            except Exception as e:
                reply(mid, {"content": [{"type": "text", "text": f"error: {e}"}], "isError": True})
        elif method.startswith("notifications/"):
            continue
        else:
            reply(mid, error={"code": -32601, "message": f"unsupported method: {method}"})


if __name__ == "__main__":
    main()
