# Minimal Vault policy scoped to specific secret paths.
# Never use wildcards in production.
#
# Apply:
#   vault policy write prod-secrets-policy prod-secrets-policy.hcl

path "secret/data/prod/registry/pull-secret" {
  capabilities = ["read"]
}

path "secret/data/dev/registry/pull-secret" {
  capabilities = ["read"]
}
