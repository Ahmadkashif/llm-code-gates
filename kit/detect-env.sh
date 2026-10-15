#!/usr/bin/env bash
# detect-env.sh — READ-ONLY report of what this machine/repo can run, and which profiles to use.
# It never installs, starts, pulls or configures anything, never sends code anywhere, and never prints keys.
# Endpoint check: GET <GATES_JUDGE_BASE_URL>/models without credentials (401/403 still means "reachable").
# Usage: bash gates/detect-env.sh [repo-dir]
set -uo pipefail
repo="${1:-.}"
say() { printf '%-22s %s\n' "$1" "$2"; }
ver() {
  command -v "$1" >/dev/null 2>&1 || { echo "absent"; return; }
  "$@" 2>/dev/null | grep -m1 -v -i 'new version' || true
}

echo "== host"
say "os" "$(uname -sr) $(uname -m)"
say "cpus" "$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo ?)"
say "ram_gb" "$(awk '/MemTotal/ {printf "%.1f", $2/1048576}' /proc/meminfo 2>/dev/null || echo ?)"
vram=0
if command -v nvidia-smi >/dev/null 2>&1; then
  gpu="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1)"
  say "gpu" "${gpu:-nvidia-smi present, query failed}"
  vram="$(printf '%s' "$gpu" | awk -F', ' '{printf "%d", $2/1024}')"
else
  say "gpu" "no nvidia-smi ($(lspci 2>/dev/null | grep -iE 'vga|3d' | head -n1 | cut -d: -f3- | sed 's/^ //' || echo unknown))"
fi
say "vram_gb" "$vram"
say "docker" "$(command -v docker >/dev/null 2>&1 && docker version --format 'client {{.Client.Version}}' 2>/dev/null || echo absent)"

echo "== tools on PATH"
for t in python3 git task semgrep gitleaks osv-scanner actionlint zizmor syft grype shellcheck hadolint; do
  say "$t" "$(ver "$t" --version)"
done
py_ok="$(python3 -c 'import sys; print("yes" if sys.version_info >= (3, 11) else "no (need >= 3.11)")' 2>/dev/null || echo no)"
say "python>=3.11" "$py_ok"

echo "== judge endpoint"
if [ -n "${GATES_JUDGE_BASE_URL:-}" ]; then
  ca=()
  [ -n "${GATES_JUDGE_CA_FILE:-}" ] && ca=(--cacert "$GATES_JUDGE_CA_FILE")
  code="$(curl -s -o /dev/null -m 5 -w '%{http_code}' "${ca[@]}" "${GATES_JUDGE_BASE_URL%/}/models" 2>/dev/null || true)"
  case "$code" in
    200|401|403) say "endpoint" "reachable (HTTP $code)";;
    000|"") say "endpoint" "UNREACHABLE";;
    *) say "endpoint" "answered HTTP $code";;
  esac
else
  say "endpoint" "GATES_JUDGE_BASE_URL not set"
fi
say "api key" "$([ -n "${GATES_JUDGE_API_KEY:-}" ] && echo 'set (not shown)' || echo 'not set')"

echo "== repo ($repo)"
stack="unknown"
[ -f "$repo/go.mod" ] && stack="go"
[ -f "$repo/package.json" ] && stack="typescript"
{ [ -f "$repo/pyproject.toml" ] || [ -f "$repo/requirements.txt" ] || [ -f "$repo/setup.py" ]; } && stack="python"
say "stack" "$stack"
say "Taskfile contract" "$(grep -Eo '^  (check:fast|check|ci|image):' "$repo/Taskfile.yml" 2>/dev/null | sed 's/^  //; s/:$//' | tr '\n' ' ' || echo 'no Taskfile.yml')"

echo "== suggestion"
judge="stub"
[ "${vram:-0}" -ge 8 ] && judge="local-8gb"
[ "${vram:-0}" -ge 48 ] && judge="local-48gb-plus"
[ -z "${GATES_JUDGE_BASE_URL:-}" ] && [ "$judge" != stub ] && judge="stub   (GPU found, but no endpoint configured)"
say "stack profile" "$stack"
say "judge profile" "$judge"
echo "next: python3 gates/render.py --stack ${stack} --judge ${judge%% *}"
