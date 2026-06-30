#!/usr/bin/env python3
"""
alert.py — drift detection notifications for managed OpenShift Terraform

Sends a Slack Block Kit message when scheduled terraform plan detects drift.

Required environment variables:
  SLACK_WEBHOOK_URL  — Slack incoming webhook URL

Optional (populated automatically by GitHub Actions):
  GITHUB_REPOSITORY, GITHUB_REF_NAME, GITHUB_RUN_ID

Usage:
  python3 scripts/alert.py "DRIFT DETECTED in rosa-production — review plan output"
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


def send_slack(message: str) -> None:
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("[alert] SLACK_WEBHOOK_URL not set — skipping Slack", file=sys.stderr)
        return

    repo = os.getenv("GITHUB_REPOSITORY", "unknown/repo")
    branch = os.getenv("GITHUB_REF_NAME", "unknown")
    run_id = os.getenv("GITHUB_RUN_ID", "0")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}"

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🟠 Terraform Drift Detected",
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

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status not in (200, 201, 202):
                print(f"[alert] Unexpected HTTP {resp.status}", file=sys.stderr)
    except urllib.error.URLError as exc:
        print(f"[alert] POST failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "Terraform drift detected"
    send_slack(msg)
    print(f"[alert] Notification sent: {msg}")
