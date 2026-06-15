# Lab Exercise Index

Hands-on steps for **Pipelines in the Wild #3 — Secrets Management Across Multi-Cloud Pipelines**.

Work through these in order. Each step builds on the previous one. The sequence is deliberate: expose the failure mode first, then fix it, then handle rotation.

| Step | File | Time | What you'll do |
|---|---|---|---|
| 0 | [00-prerequisites.md](lab/00-prerequisites.md) | 15 min | Verify tools, cluster access, and provider account |
| 1 | [01-expose-the-gap.md](lab/01-expose-the-gap.md) | 20 min | Deploy without RBAC — prove any SA can read secrets |
| 2 | [02-install-eso.md](lab/02-install-eso.md) | 15 min | Install External Secrets Operator and verify health |
| 3 | [03-configure-secretstore.md](lab/03-configure-secretstore.md) | 25 min | Configure SecretStore for your chosen provider |
| 4 | [04-sync-pull-secret.md](lab/04-sync-pull-secret.md) | 20 min | Apply ExternalSecret and verify sync |
| 5 | [05-apply-rbac.md](lab/05-apply-rbac.md) | 15 min | Lock down namespace secret access |
| 6 | [06-trigger-rotation.md](lab/06-trigger-rotation.md) | 30 min | Rotate credential, observe lag, restart pods |
| 7 | [07-rotation-runbook-exercise.md](lab/07-rotation-runbook-exercise.md) | 20 min | Fill in the rotation runbook for your environment |

**Total estimated time:** ~2.5 hours

## Provider Selection

Pick one provider for the lab. All three are supported:

- **AWS Secrets Manager** — `manifests/secretstore/*-secretstore-aws.yaml`
- **Azure Key Vault** — `manifests/secretstore/*-secretstore-azure.yaml`
- **HashiCorp Vault** — `manifests/secretstore/*-secretstore-vault.yaml` + `vault/kubernetes-auth-setup.sh`

## Cleanup

```bash
oc delete externalsecret registry-pull-secret -n dev
oc delete secretstore dev-secretstore -n dev
oc delete -f manifests/rbac/dev-secret-rbac.yaml
oc delete -f manifests/namespace/dev-namespace.yaml
```

Do not delete prod resources unless this is a dedicated lab cluster.
