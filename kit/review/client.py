"""Minimal OpenAI-compatible chat-completions client (stdlib urllib). Concurrency 1, timeouts, bounded retries.

The API key is read from the environment variable NAMED by the judge profile (api_key_env); it is never logged,
never written to reports, and never sent anywhere but the configured base_url.
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request


class JudgeError(RuntimeError):
    pass


class OpenAICompatClient:
    def __init__(self, judge: dict):
        self.base = judge["base_url"].rstrip("/")
        self.model = judge["model"]
        self.timeout = float(judge.get("timeout_s", 120))
        self.retries = int(judge.get("retries", 2))
        self.params = judge.get("params", {}) or {}
        self.extra_body = judge.get("extra_body", {}) or {}
        self.response_format = judge.get("response_format")  # None | "json_object" | "json_schema"
        key_env = judge.get("api_key_env") or ""
        self._key = os.environ.get(key_env, "") if key_env else ""
        if key_env and not self._key and judge.get("api_key_required", True):
            raise JudgeError(f"judge profile needs an API key in ${key_env} (not set)")
        ca = os.environ.get(judge.get("ca_file_env") or "", "") or judge.get("ca_file") or ""
        # TLS is always verified; a private CA (e.g. a home gateway's) is added via a CA file, never by disabling checks
        self.ctx = ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()
        self.calls = 0

    def chat(self, messages: list[dict], schema: dict | None = None, seed: int | None = None) -> dict:
        body = {"model": self.model, "messages": messages, **self.params, **self.extra_body}
        if seed is not None:
            body["seed"] = seed
        if self.response_format == "json_object":
            body["response_format"] = {"type": "json_object"}
        elif self.response_format == "json_schema" and schema:
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "gates_output", "schema": schema, "strict": False}}
        data = json.dumps(body).encode()
        headers = {"Content-Type": "application/json", "User-Agent": "llm-code-gates/0.1"}
        if self._key:
            headers["Authorization"] = f"Bearer {self._key}"
        last = None
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(f"{self.base}/chat/completions", data=data, headers=headers, method="POST")
            t0 = time.monotonic()
            self.calls += 1
            try:
                with urllib.request.urlopen(req, timeout=self.timeout, context=self.ctx) as r:
                    resp = json.loads(r.read().decode())
                choice = resp["choices"][0]
                msg = choice.get("message", {})
                content = msg.get("content") or ""
                return {"content": content, "reasoning": msg.get("reasoning_content") or msg.get("reasoning") or "",
                        "finish_reason": choice.get("finish_reason"), "usage": resp.get("usage", {}),
                        "latency_s": round(time.monotonic() - t0, 3), "attempt": attempt + 1}
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}"
                if e.code not in (408, 409, 425, 429, 500, 502, 503, 504):
                    raise JudgeError(last) from None
            except (urllib.error.URLError, TimeoutError, OSError, KeyError, json.JSONDecodeError) as e:
                last = f"{type(e).__name__}: {e}"
            time.sleep(min(8.0, 0.5 * 2 ** attempt))
        raise JudgeError(f"judge unavailable after {self.retries + 1} attempts: {last}")
