#!/usr/bin/env python3
"""Local mock of an OpenAI-compatible /v1/chat/completions endpoint, answered by the stub judge.

Used by the kit's tests and by Q14's protocol check: it exercises the real HTTP client, auth header, retries,
timeouts and reply parsing without any model. Binds 127.0.0.1 only. Fault injection:
  --fail-first N   return HTTP 503 for the first N requests
  --think          always prepend a qwen3-style <think> block
  --garbage-every K  every K-th reply is not JSON at all
  --require-key ENV  demand 'Authorization: Bearer $ENV' (value read from the environment, never printed)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stub_judge  # noqa: E402


def make_handler(opts):
    state = {"n": 0, "log": []}
    lock = threading.Lock()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _json(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path.rstrip("/").endswith("/models"):
                return self._json(200, {"object": "list", "data": [{"id": opts.model, "object": "model"}]})
            self._json(404, {"error": "not found"})

        def do_POST(self):
            with lock:
                state["n"] += 1
                n = state["n"]
            if not self.path.endswith("/chat/completions"):
                return self._json(404, {"error": "not found"})
            if opts.require_key:
                want = os.environ.get(opts.require_key, "")
                if self.headers.get("Authorization") != f"Bearer {want}":
                    return self._json(401, {"error": "bad key"})
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            state["log"].append({"n": n, "model": body.get("model"), "response_format": body.get("response_format"),
                                 "temperature": body.get("temperature")})
            if n <= opts.fail_first:
                return self._json(503, {"error": "warming up"})
            msgs = body["messages"]
            content = stub_judge.respond(stub_judge.prompt_id_from(msgs), msgs)
            if opts.think and not content.startswith("<think>"):
                content = "<think>\nLet me think about this diff.\n</think>\n" + content
            if opts.garbage_every and n % opts.garbage_every == 0:
                content = "I cannot comply with the JSON format today."
            self._json(200, {"id": f"mock-{n}", "object": "chat.completion", "model": body.get("model"),
                             "choices": [{"index": 0, "finish_reason": "stop",
                                          "message": {"role": "assistant", "content": content}}],
                             "usage": {"prompt_tokens": sum(len(m["content"]) // 4 for m in msgs),
                                       "completion_tokens": len(content) // 4}})
    H.state = state
    return H


def serve(port=0, **kw):
    class Opts:  # simple options object
        model = kw.get("model", "mock-model")
        fail_first = kw.get("fail_first", 0)
        think = kw.get("think", False)
        garbage_every = kw.get("garbage_every", 0)
        require_key = kw.get("require_key", "")
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Opts))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--model", default="mock-model")
    ap.add_argument("--fail-first", type=int, default=0)
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--garbage-every", type=int, default=0)
    ap.add_argument("--require-key", default="")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(a))
    print(f"mock OpenAI-compatible server on http://127.0.0.1:{srv.server_address[1]}/v1", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
