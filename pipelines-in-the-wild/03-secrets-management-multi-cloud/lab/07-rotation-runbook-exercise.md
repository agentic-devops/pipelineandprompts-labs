# Step 7 — Rotation Runbook Exercise

**Time:** ~20 minutes  
**Goal:** Fill in the rotation runbook template for your own environment.

## Instructions

1. Open [docs/rotation-runbook.md](../docs/rotation-runbook.md)
2. Copy it to your team's runbook system (Confluence, Notion, internal wiki, or `docs/rotation-runbook-prod.md` in your platform repo)
3. Fill in every `[OWNER]`, `[CONTACT]`, and `[LIST ...]` placeholder
4. Name real people — not roles like "the platform team"

## Required Fields

| Placeholder | What to fill in |
|---|---|
| `[OWNER]` | Actual name of the person with authority |
| `[CONTACT]` | Slack handle, phone, or PagerDuty escalation |
| `[LIST DEPLOYMENTS...]` | Every deployment using `imagePullSecrets: registry-pull-secret` |
| `[SLACK CHANNEL...]` | Your incident bridge channel |
| `[YES/NO]` | Whether change management approval is required before rotation |

## Validation Exercise

Answer these questions in your completed runbook:

1. **Who approves a prod credential rotation at 2 AM?**
2. **Who runs `oc rollout restart` after ESO confirms sync?**
3. **Who confirms the application is healthy post-restart?**
4. **What is the escalation path if sync fails?**
5. **What is the rollback procedure if the new credential is wrong?**

If you cannot answer all five with a named person, the runbook is not complete.

## Peer Review

Have a colleague who was not involved in this lab review your runbook. They should be able to execute a rotation using only the runbook — no Slack, no tribal knowledge.

## Store It

Put the completed runbook somewhere a new team member can find it without asking:

- Linked from your platform team's onboarding doc
- Referenced in your on-call runbook index
- Stored in the same repo as your deployment manifests

## Done

You've completed the lab. The technical architecture is in place. The human routing problem is documented.

Return to [LAB.md](../LAB.md) for cleanup steps.
