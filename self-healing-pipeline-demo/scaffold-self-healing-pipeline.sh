#!/usr/bin/env bash
# scaffold-self-healing-pipeline.sh
#
# One-shot setup for the self-healing-pipeline-demo repo.
# Clones the repo, initialises git, and prints the exact
# gh secret set commands for your environment.
#
# Usage: bash scaffold-self-healing-pipeline.sh <app-name> <server-ip>
# Example: bash scaffold-self-healing-pipeline.sh waybill 10.0.0.42

set -euo pipefail

APP="${1:-waybill}"
SERVER_IP="${2:-}"

if [ -z "$SERVER_IP" ]; then
  echo "Usage: $0 <app-name> <server-ip>"
  echo "Example: $0 waybill 10.0.0.42"
  exit 1
fi

echo ""
echo "=== Self-Healing Pipeline Scaffold ==="
echo "App:    $APP"
echo "Server: $SERVER_IP"
echo ""

# ── Verify prerequisites ──────────────────────────────────────────────────────
echo "[check] Verifying prerequisites..."
for cmd in git docker gh; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ $cmd not found — install it before continuing"
    exit 1
  fi
done
echo "✅ git, docker, gh all present"
echo ""

# ── Verify gh auth ────────────────────────────────────────────────────────────
if ! gh auth status &>/dev/null; then
  echo "❌ Not authenticated with GitHub CLI"
  echo "   Run: gh auth login"
  exit 1
fi
echo "✅ GitHub CLI authenticated"
echo ""

# ── Print secret setup commands ───────────────────────────────────────────────
echo "=== GitHub Secrets Setup ==="
echo ""
echo "Run these commands to set your pipeline secrets."
echo "Replace placeholder values with real ones before running."
echo ""

cat << SECRETS
# Server IP (no quotes needed)
gh secret set SERVER_IP --body "$SERVER_IP"

# SSH private key — paste the full key content from bootstrap-server.sh output
# or from your key file:
gh secret set SSH_PRIVATE_KEY < ~/.ssh/deploy_ed25519

# Strong random password — generate one:
#   openssl rand -hex 32
gh secret set POSTGRES_PASSWORD --body "REPLACE_WITH_STRONG_PASSWORD"

# Slack incoming webhook URL
gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/services/REPLACE/WITH/YOUR_WEBHOOK"

# PagerDuty Events API v2 routing key — scope to this service only
gh secret set PAGERDUTY_ROUTING_KEY --body "REPLACE_WITH_PAGERDUTY_ROUTING_KEY"

SECRETS

echo "=== Local Dev Quick Start ==="
echo ""
echo "cd waybill"
echo "cp .env.example .env"
echo "docker build -t $APP:local ."
echo "IMAGE_NAME=$APP BLUE_TAG=local GREEN_TAG=local docker compose up"
echo ""
echo "Then in another terminal:"
echo "bash scripts/smoke-test.sh localhost blue"
echo "bash scripts/smoke-test.sh localhost green"
echo ""
echo "=== Port Layout ==="
echo ""
echo "  waybill-blue:  http://localhost:7070"
echo "  waybill-green: http://localhost:9091"
echo "  postgres:      localhost:5433 (localhost only)"
echo ""
echo "Override ports if needed:"
echo "  BLUE_PORT=8080 bash scripts/smoke-test.sh localhost blue"
echo ""
echo "=== Test Alerting Locally ==="
echo ""
echo "# TRANSIENT — silent (no env vars needed)"
echo "python3 scripts/alert.py \"registry connection timeout on push\""
echo ""
echo "# DEGRADED — Slack warning"
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/... \\"
echo "  python3 scripts/alert.py \"smoke test failed on main\""
echo ""
echo "# CRITICAL — Slack + PagerDuty"
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/... \\"
echo "PAGERDUTY_ROUTING_KEY=your-key \\"
echo "  python3 scripts/alert.py \"deploy failed on main\""
echo ""
echo "=== Done ==="
echo ""
echo "Full article: https://pipelineandprompts.dev/pipelines-in-the-wild/02"
echo ""
