# Prompt Versioning CI Gate for OpenShift

Enforces schema validation, secret scanning, and model governance for LLM prompts before they reach your AI workflows on OpenShift. Prompts are versioned in Git, validated via GitHub Actions, and synced to OpenShift as ConfigMaps.

## Prerequisites

- OpenShift 4.14+
- `oc` CLI 4.14+
- Python 3.11+
- gitleaks 8.x
- GitHub Actions enabled
- Branch protection on `main` branch

## Quick Start

1. **Configure secrets in GitHub repository settings:**
   ```
   OPENSHIFT_SERVER: https://api.your-cluster.example.com:6443
   OPENSHIFT_TOKEN: sha256~your-token-here
   ```

2. **Create the target namespace:**
   ```bash
   oc create namespace ai-workflows
   oc apply -f manifests/rbac.yaml
   ```

3. **Enable branch protection:**
   - Navigate to Settings → Branches → Add rule
   - Branch name pattern: `main`
   - Require status checks: `schema-validate`, `secret-scan`, `model-pin-check`

4. **Test the gate:**
   ```bash
   # Make a change to any prompt
   git checkout -b test-gate
   # Edit prompts/rosa-hcp-deploy.yaml
   git add prompts/
   git commit -m "test: trigger CI gate"
   git push origin test-gate
   # Open PR and observe checks
   ```

## Directory Structure

```
prompt-versioning-ci-openshift/
├── README.md                      # This file
├── .prompt-policy.yaml            # Approved model versions
├── .gitleaks.toml                 # Secret detection rules
├── prompts/                       # Versioned prompt manifests
│   └── rosa-hcp-deploy.yaml       # Example: ROSA HCP deployment prompt
├── scripts/
│   ├── validate_prompts.py        # Schema validator (CI gate)
│   ├── check_model_pins.py        # Model policy enforcer (CI gate)
│   ├── split_registry.py          # ConfigMap generator by domain
│   └── audit_query.sh             # Query ConfigMap access logs
├── manifests/
│   └── rbac.yaml                  # ServiceAccount + Role for prompt consumers
└── .github/workflows/
    ├── prompt-gate.yml            # CI gate: validate + scan + policy check
    └── sync-prompts.yml           # Sync approved prompts to OpenShift
```

## Workflow

1. Developer modifies a prompt in `prompts/` directory
2. PR triggers `prompt-gate.yml`: schema validation, secret scan, model policy check
3. On merge to `main`, `sync-prompts.yml` updates the ConfigMap in OpenShift
4. Applications read prompts from ConfigMap using the `prompt-consumer` ServiceAccount

## Known Limitations

- **ConfigMap size limit:** 1MB total. Split large prompt sets using `scripts/split_registry.py`
- **Model pin false confidence:** Policy check validates string matches only—does not verify model availability with provider APIs
- **Sync is eventual:** ConfigMap update triggers on push; consuming pods must refresh their volume mounts or restart to see changes
- **No rollback automation:** Failed deployments require manual git revert and re-sync

## Full Implementation Walkthrough

See the complete guide at:  
[AI in the Stack #4 — Treat Prompts Like Code: A CI Gate for LLM Workflows on OpenShift](https://pipelineandprompts.com/posts/prompt-versioning-ci-openshift/)
