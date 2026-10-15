#!/usr/bin/env python3
"""Turn a claude --output-format stream-json log into a readable transcript (tool calls, results, hook feedback)."""
import json, sys
def short(s, n=420):
    s = " | ".join(str(s).splitlines()); return s if len(s) <= n else s[:n] + " ..."
for line in open(sys.argv[1]):
    try: e = json.loads(line)
    except json.JSONDecodeError: continue
    t = e.get("type")
    if t == "system" and e.get("subtype") == "init":
        print(f"INIT model={e.get('model')} permission={e.get('permissionMode')} cwd=<scratch>/q17/work")
    elif t == "system" and "hook" in str(e.get("subtype", "")):
        print(f"HOOK  {e.get('subtype')}: {short(e.get('output') or e.get('stderr') or e.get('content') or e)}")
    elif t == "assistant":
        for c in e["message"].get("content", []):
            if c.get("type") == "text" and c["text"].strip(): print("ASSISTANT  " + short(c["text"]))
            elif c.get("type") == "tool_use": print("TOOL_USE   " + short(c["input"].get("command") or json.dumps(c["input"])))
    elif t == "user":
        content = e.get("message", {}).get("content", [])
        if isinstance(content, str):
            print("USER/HOOK  " + short(content)); continue
        for c in content:
            if c.get("type") == "tool_result":
                body = c.get("content"); body = body if isinstance(body, str) else " ".join(x.get("text", "") for x in body or [])
                print(("TOOL_RESULT [blocked] " if c.get("is_error") else "TOOL_RESULT ") + short(body))
            elif c.get("type") == "text": print("USER/HOOK  " + short(c["text"]))
    elif t == "result":
        print(f"RESULT     {e.get('subtype')} turns={e.get('num_turns')} cost_usd={e.get('total_cost_usd')} duration_s={round(e.get('duration_ms',0)/1000,1)}")
