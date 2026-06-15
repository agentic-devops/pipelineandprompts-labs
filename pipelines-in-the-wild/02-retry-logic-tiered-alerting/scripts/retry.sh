#!/usr/bin/env bash
# retry.sh — exponential backoff retry wrapper
#
# Usage: source scripts/retry.sh
#        retry <max_attempts> <initial_delay_seconds> <command...>
#
# Example:
#   source scripts/retry.sh
#   retry 4 10 docker push ghcr.io/org/image:sha
#   retry 3 8 bash scripts/smoke-test.sh $SERVER blue

retry() {
  local max_attempts=$1
  local delay=$2
  shift 2
  local cmd=("$@")
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "[retry] Attempt $attempt/$max_attempts: ${cmd[*]}"

    if "${cmd[@]}"; then
      echo "[retry] ✅ Succeeded on attempt $attempt"
      return 0
    fi

    if [ $attempt -lt $max_attempts ]; then
      # Exponential backoff with jitter (floor 1s, cap 60s)
      # Jitter range is ±1-2s at low delays, wider at higher delays
      local raw_jitter=$(( RANDOM % (delay / 5 + 2) - delay / 10 ))
      local wait=$(( delay + raw_jitter ))
      wait=$(( wait < 1 ? 1 : wait ))
      wait=$(( wait > 60 ? 60 : wait ))
      echo "[retry] ⏳ Waiting ${wait}s before retry (attempt $((attempt+1)))..."
      sleep "$wait"
      delay=$(( delay * 2 > 60 ? 60 : delay * 2 ))
    fi

    attempt=$(( attempt + 1 ))
  done

  echo "[retry] ❌ All $max_attempts attempts failed: ${cmd[*]}"
  return 1
}

export -f retry
