#!/usr/bin/env bash
# Switch PolicyAI's LLM provider between Claude (Anthropic) and Groq (free,
# OpenAI-compatible). Edits .env in place, then you restart the worker so it
# re-reads the env. See `make llm-claude`, `make llm-groq`, `make llm-status`.
#
# Groq is the free fallback while Anthropic credits are unavailable; Claude gives
# the best extraction/mapping quality once credits are topped up.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
MODE="${1:-status}"

# Groq defaults (OpenAI-compatible endpoint + a strong tool-calling model).
GROQ_BASE_URL="https://api.groq.com/openai/v1"
GROQ_MODEL="llama-3.3-70b-versatile"

[ -f "$ENV_FILE" ] || { echo "No .env at $ENV_FILE"; exit 1; }

# set_kv KEY VALUE — replace an existing KEY= line or append it.
set_kv() {
  local key="$1" val="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    # Use a temp file; portable across macOS/Linux sed differences.
    python3 - "$ENV_FILE" "$key" "$val" <<'PY'
import sys
path, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path).read().splitlines()
out = []
for ln in lines:
    if ln.startswith(key + "="):
        out.append(f"{key}={val}")
    else:
        out.append(ln)
open(path, "w").write("\n".join(out) + "\n")
PY
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}

current() {
  grep -E "^LLM_PROVIDER=" "$ENV_FILE" | head -1 | cut -d= -f2 || echo "anthropic (default)"
}

case "$MODE" in
  groq)
    set_kv LLM_PROVIDER openai_compatible
    set_kv OPENAI_BASE_URL "$GROQ_BASE_URL"
    set_kv LLM_MODEL "$GROQ_MODEL"
    if ! grep -qE "^OPENAI_API_KEY=.+" "$ENV_FILE"; then
      set_kv OPENAI_API_KEY ""
      echo "NOTE: OPENAI_API_KEY is empty. Paste your free Groq key (https://console.groq.com/keys) into .env."
    fi
    echo "LLM provider -> Groq ($GROQ_MODEL). Restart the worker: make dev-api"
    ;;
  claude)
    set_kv LLM_PROVIDER anthropic
    echo "LLM provider -> Claude (extraction=sonnet, mapping=opus). Restart the worker: make dev-api"
    ;;
  status)
    prov="$(current)"
    echo "LLM_PROVIDER = $prov"
    if [ "$prov" = "openai_compatible" ]; then
      echo "  base_url = $(grep -E '^OPENAI_BASE_URL=' "$ENV_FILE" | cut -d= -f2-)"
      echo "  model    = $(grep -E '^LLM_MODEL=' "$ENV_FILE" | cut -d= -f2-)"
      grep -qE "^OPENAI_API_KEY=.+" "$ENV_FILE" && echo "  api_key  = set" || echo "  api_key  = MISSING (paste Groq key into .env)"
    else
      grep -qE "^ANTHROPIC_API_KEY=.+" "$ENV_FILE" && echo "  api_key  = set" || echo "  api_key  = MISSING"
    fi
    ;;
  *)
    echo "usage: llm_switch.sh {groq|claude|status}"; exit 1;;
esac
