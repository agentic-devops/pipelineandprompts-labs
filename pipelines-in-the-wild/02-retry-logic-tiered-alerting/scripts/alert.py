#!/usr/bin/env python3
"""
alert.py — tiered pipeline alerting

Severity tiers:
  TRANSIENT → silent discard (no notification)
  DEGRADED  → Slack warning (Block Kit)
  CRITICAL  → Slack + PagerDuty page

Required environment variables (set as GitHub Actions secrets):
  SLACK_WEBHOOK_URL      — Slack incoming webhook URL
  PAGERDUTY_ROUTING_KEY  — Events API v2 key, scoped to this service only

Optional (populated automatically by GitHub Actions):
  GITHUB_REPOSITORY, GITHUB_REF_NAME, GITHUB_RUN_ID, GITHUB_SHA

Usage:
  python3 scripts/alert.py "error message string"

Test locally (no secrets needed for TRANSIENT):
  python3 scripts/alert.py "registry connection timeout on push"

  SLACK_WEBHOOK_URL=https://hooks.slack.com/... \\
    python3 scripts/alert.py "smoke test failed on main"

  SLACK_WEBHOOK_URL=https://hooks.slack.com/... \\
  PAGERDUTY_ROUTING_KEY=your-key \\
    python3 scripts/alert.py "deploy failed on main"
"""

import os
import sys
import json
import urllib.request
import urllib.error
from enum import Enum
from datetime import datetime, timezone


class Severity(Enum):
    TRANSIENT = "transient"
    DEGRADED  = "degraded"
    CRITICAL  = "critical"


# Keep TRANSIENT patterns as specific as possible.
# Broad patterns risk silencing a real failure whose error message
# happens to contain a transient-sounding substring.
# Review these monthly for the first 3 months after deployment.
# Update whenever a new pipeline step is added.
ERROR_PATTERNS: dict[Severity, list[str]] = {
    Severity.TRANSIENT: [
        "registry connection timeout",
        "registry unavailable",
        "registry rate limit",
        "registry 503",
        "registry 502",
        "i/o timeout",
        "connection refused to registry",
        "429 too many requests",
    ],
    Severity.DEGRADED: [
        "smoke test failed",
        "slow response",
        "health check degraded",
        "non-zero exit code",
    ],
    Severity.CRITICAL: [
        "deploy failed",
        "rollback required",
        "production down",
        "slot swap failed",
        "health check failed",
        "container crashed",
    ],
}


def classify(error_msg: str) -> Severity:
    msg = error_msg.lower()
    for severity, patterns in ERROR_PATTERNS.items():
        if any(p in msg for p in patterns):
            return severity
    # Unknown patterns default to DEGRADED — never silenced.
    # An attacker who can influence error messages cannot guarantee silence.
    return Severity.DEGRADED


def _post(url: str, payload: dict, timeout: int = 10) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status not in (200, 201, 202):
                print(f"[alert] Unexpected HTTP {resp.status}", file=sys.stderr)
    except urllib.error.URLError as exc:
        print(f"[alert] POST failed ({url}): {exc}", file=sys.stderr)


def send_slack(message: str, severity: Severity) -> None:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("[alert] SLACK_WEBHOOK_URL not set — skipping Slack", file=sys.stderr)
        return

    repo   = os.getenv("GITHUB_REPOSITORY", "unknown/repo")
    branch = os.getenv("GITHUB_REF_NAME",   "unknown")
    run_id = os.getenv("GITHUB_RUN_ID",      "0")
    ts     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    icons = {Severity.DEGRADED: "🟡", Severity.CRITICAL: "🔴"}
    icon  = icons.get(severity, "⚪")

    run_url = f"https://github.com/{repo}/actions/runs/{run_id}"

    # Block Kit payload — compatible with all current Slack workspace configurations.
    # The legacy Attachments API is deprecated for incoming webhooks.
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{icon} [{severity.value.upper()}] Pipeline Alert",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{message}*"},
                "fields": [
                    {"type": "mrkdwn", "text": f"*Branch*\n{branch}"},
                    {"type": "mrkdwn", "text": f"*Run*\n<{run_url}|{run_id}>"},
                    {"type": "mrkdwn", "text": f"*Repo*\n{repo}"},
                    {"type": "mrkdwn", "text": f"*Time*\n{ts}"},
                ],
            },
            {"type": "divider"},
        ]
    }
    _post(webhook, payload)


def send_pagerduty(message: str) -> None:
    key = os.environ.get("PAGERDUTY_ROUTING_KEY")
    if not key:
        print("[alert] PAGERDUTY_ROUTING_KEY not set — skipping PagerDuty", file=sys.stderr)
        return

    repo   = os.getenv("GITHUB_REPOSITORY", "unknown/repo")
    run_id = os.getenv("GITHUB_RUN_ID", "0")
    # dedup_key groups all alerts from the same run into one incident.
    # Without it, a flapping pipeline opens a new incident on every failure.
    # A resolve event keyed to the same value closes the incident automatically.
    dedup_key = f"{repo}/run/{run_id}"

    payload = {
        "routing_key":  key,
        "event_action": "trigger",
        "dedup_key":    dedup_key,
        "payload": {
            "summary":  message,
            "severity": "critical",
            "source":   "github-actions",
            "custom_details": {
                "repository": repo,
                "run_id":     run_id,
                "sha":        os.getenv("GITHUB_SHA"),
            },
        },
    }
    _post("https://events.pagerduty.com/v2/enqueue", payload)


def alert(error_msg: str) -> None:
    severity = classify(error_msg)

    if severity == Severity.TRANSIENT:
        print("[alert] Transient pattern matched — no notification sent")
        return

    send_slack(error_msg, severity)

    if severity == Severity.CRITICAL:
        send_pagerduty(error_msg)
        print("[alert] 🚨 Critical — Slack + PagerDuty triggered")
    else:
        print("[alert] ⚠️  Degraded — Slack warning sent")


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Unknown pipeline failure"
    alert(msg)
