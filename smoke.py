"""Smoke test novai-router MCP."""
import json
import subprocess
import sys

SERVER = r'C:\Users\32065\Documents\deepseek-harness\default-workspace\novai-marketing\mcp-router\server.py'
reqs = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "pick_model", "arguments": {"task": "coding", "limit": 4}}},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "compare_models", "arguments": {"models": ["deepseek-v4-pro", "kimi-k2.7-code", "glm-5.3"]}}},
    {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "pick_model", "arguments": {"task": "image", "limit": 3}}},
]
p = subprocess.run([sys.executable, SERVER], input=("\n".join(json.dumps(r) for r in reqs) + "\n").encode(),
                   capture_output=True, timeout=120)
print('rc:', p.returncode, p.stderr.decode()[:200])
for line in p.stdout.decode().splitlines():
    d = json.loads(line)
    if d.get('id') == 1:
        print('init ->', d['result']['serverInfo'])
    elif d.get('id') == 2:
        print('tools:', [t['name'] for t in d['result']['tools']])
    else:
        print(f"--- id {d['id']} ---")
        print(d['result']['content'][0]['text'][:420])
