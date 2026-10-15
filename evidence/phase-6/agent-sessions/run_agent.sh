#!/usr/bin/env bash
# Run one short headless Claude Code session in a scratch clone of the sample repo (main) to produce a change set.
# Usage: run_agent.sh <id> "<task prompt>"
set -uo pipefail
id="$1"; task="$2"
here="$(cd "$(dirname "$0")" && pwd)"
sample="$here/../../sample-service"
work="$here/$id"
rm -rf "$work"; git clone -q "$sample" "$work"; cd "$work" || exit 1
git checkout -q main
export PATH="$here/../../tools/bin:$here/../../tools/venv/bin:$PATH"
start=$(date +%s)
timeout 900 claude -p "$task" --model haiku --setting-sources project --no-session-persistence \
  --permission-mode acceptEdits --max-budget-usd 1.00 \
  --allowedTools "Read" "Edit" "Write" "Glob" "Grep" "Bash(python3 -m pytest:*)" "Bash(git diff:*)" "Bash(git status:*)" \
  --output-format stream-json --verbose > "$here/$id.stream.jsonl" 2> "$here/$id.stderr.txt"
echo "rc=$? wall_s=$(( $(date +%s) - start ))" > "$here/$id.result.txt"
git status --short >> "$here/$id.result.txt"
