#!/usr/bin/env bash
# Switch PolicyAI's LLM provider. Edits .env in place, then restart the worker so
# it re-reads the env. See `make llm-<provider>` and `make llm-status`.
#
# Providers (all free tiers except Claude):
#   claude     Anthropic (best quality; extraction=sonnet, mapping=opus). Paid.
#   groq       Groq llama-3.3-70b. 12k tokens/request, ~100k tokens/day free.
#   cerebras   Cerebras llama-3.3-70b. 60k TPM, ~1M tokens/day free: best free bulk.
#   gemini     Google gemini-2.5-flash via the OpenAI-compatible endpoint.
#   mistral    Mistral small via La Plateforme (generous free experiment tier).
#   openrouter OpenRouter free model pool (rate limits vary by model).
#
# Each provider keeps its key in its own .env slot (GROQ_API_KEY, CEREBRAS_API_KEY,
# GEMINI_API_KEY, MISTRAL_API_KEY, OPENROUTER_API_KEY); switching copies the active
# one into OPENAI_API_KEY, which is what the client reads.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
MODE="${1:-status}"

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

get_kv() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- || true; }

current() { get_kv LLM_PROVIDER || echo "anthropic (default)"; }

# use_openai_compatible NAME BASE_URL MODEL KEY_SLOT KEY_URL [TPM_LIMIT]
use_openai_compatible() {
  local name="$1" base="$2" model="$3" slot="$4" key_url="$5" tpm="${6:-0}"
  set_kv LLM_PROVIDER openai_compatible
  set_kv OPENAI_BASE_URL "$base"
  set_kv LLM_MODEL "$model"
  set_kv OPENAI_TPM_LIMIT "$tpm"
  local key
  key="$(get_kv "$slot")"
  if [ -n "$key" ]; then
    set_kv OPENAI_API_KEY "$key"
  else
    echo "NOTE: $slot is empty in .env. Create a free key at $key_url and add: $slot=<key>"
    echo "      then re-run this switch so it becomes the active OPENAI_API_KEY."
  fi
  echo "LLM provider -> $name ($model). Restart the worker: make dev-api"
}

case "$MODE" in
  groq)
    # Migrate a legacy setup where the Groq key only lives in OPENAI_API_KEY.
    if [ -z "$(get_kv GROQ_API_KEY)" ] && [ "$(get_kv OPENAI_BASE_URL)" = "https://api.groq.com/openai/v1" ] && [ -n "$(get_kv OPENAI_API_KEY)" ]; then
      set_kv GROQ_API_KEY "$(get_kv OPENAI_API_KEY)"
    fi
    use_openai_compatible Groq "https://api.groq.com/openai/v1" "llama-3.3-70b-versatile" GROQ_API_KEY "https://console.groq.com/keys" 12000
    ;;
  cerebras)
    use_openai_compatible Cerebras "https://api.cerebras.ai/v1" "gpt-oss-120b" CEREBRAS_API_KEY "https://cloud.cerebras.ai" 60000
    ;;
  gemini)
    use_openai_compatible Gemini "https://generativelanguage.googleapis.com/v1beta/openai/" "gemini-2.5-flash" GEMINI_API_KEY "https://aistudio.google.com/apikey" 0
    ;;
  mistral)
    use_openai_compatible Mistral "https://api.mistral.ai/v1" "mistral-small-latest" MISTRAL_API_KEY "https://console.mistral.ai/api-keys" 0
    ;;
  openrouter)
    use_openai_compatible OpenRouter "https://openrouter.ai/api/v1" "meta-llama/llama-3.3-70b-instruct:free" OPENROUTER_API_KEY "https://openrouter.ai/keys" 0
    ;;
  claude)
    set_kv LLM_PROVIDER anthropic
    echo "LLM provider -> Claude (extraction=sonnet, mapping=opus). Restart the worker: make dev-api"
    ;;
  status)
    prov="$(current)"
    echo "LLM_PROVIDER = $prov"
    if [ "$prov" = "openai_compatible" ]; then
      echo "  base_url  = $(get_kv OPENAI_BASE_URL)"
      echo "  model     = $(get_kv LLM_MODEL)"
      echo "  tpm_limit = $(get_kv OPENAI_TPM_LIMIT)"
      grep -qE "^OPENAI_API_KEY=.+" "$ENV_FILE" && echo "  api_key   = set" || echo "  api_key   = MISSING"
    else
      grep -qE "^ANTHROPIC_API_KEY=.+" "$ENV_FILE" && echo "  api_key   = set" || echo "  api_key   = MISSING"
    fi
    echo "  key slots : groq=$( [ -n "$(get_kv GROQ_API_KEY)" ] && echo set || echo - ) cerebras=$( [ -n "$(get_kv CEREBRAS_API_KEY)" ] && echo set || echo - ) gemini=$( [ -n "$(get_kv GEMINI_API_KEY)" ] && echo set || echo - ) mistral=$( [ -n "$(get_kv MISTRAL_API_KEY)" ] && echo set || echo - ) openrouter=$( [ -n "$(get_kv OPENROUTER_API_KEY)" ] && echo set || echo - )"
    ;;
  *)
    echo "usage: llm_switch.sh {claude|groq|cerebras|gemini|mistral|openrouter|status}"; exit 1;;
esac
