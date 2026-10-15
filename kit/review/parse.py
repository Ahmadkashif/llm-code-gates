"""Robust extraction of one JSON object from a model reply (stdlib only).

Handles: <think>...</think> blocks (closed, unclosed, or empty as qwen3 emits with /no_think), markdown fences,
prose before/after the object, trailing commas, Python literals (True/False/None) outside strings, and
smart quotes used as JSON delimiters. It never evaluates code. Returns (obj, error).
"""
from __future__ import annotations

import json
import re

THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
FENCE = re.compile(r"```(?:json|JSON)?\s*\n(.*?)```", re.S)


def strip_reasoning(text: str) -> str:
    text = THINK.sub("", text)
    low = text.lower()
    if "</think>" in low:  # opening tag lost (some servers strip it)
        text = text[low.rfind("</think>") + len("</think>"):]
    elif "<think>" in low:  # unclosed: the model ran out of tokens while thinking, or answered inside it
        text = text[low.find("<think>") + len("<think>"):]
    return text.strip()


def _balanced_objects(text: str):
    """Yield every top-level {...} substring, string-aware."""
    depth, start, in_str, esc = 0, None, False, False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start:i + 1]
                start = None


def _repair(s: str) -> str:
    s = s.replace("“", '"').replace("”", '"')
    out, in_str, esc = [], False, False
    i = 0
    while i < len(s):
        ch = s[i]
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        for lit, rep in (("True", "true"), ("False", "false"), ("None", "null")):
            if s.startswith(lit, i) and not (s[i - 1:i].isalnum()) and not s[i + len(lit):i + len(lit) + 1].isalnum():
                out.append(rep)
                i += len(lit)
                break
        else:
            out.append(ch)
            i += 1
    s = "".join(out)
    return re.sub(r",\s*([}\]])", r"\1", s)


def extract_json(text: str):
    """Return (dict, None) or (None, error message)."""
    if not text or not text.strip():
        return None, "empty reply"
    body = strip_reasoning(text)
    candidates = [m.group(1) for m in FENCE.finditer(body)] + [body]
    last_err = "no JSON object found"
    for cand in candidates:
        objs = list(_balanced_objects(cand))
        # prefer the largest object (the answer), not an example fragment
        for o in sorted(objs, key=len, reverse=True):
            for attempt in (o, _repair(o)):
                try:
                    val = json.loads(attempt)
                    if isinstance(val, dict):
                        return val, None
                except json.JSONDecodeError as e:
                    last_err = f"invalid JSON: {e}"
    return None, last_err
