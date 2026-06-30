# Governance Prerequisites Checklist

Hard stops before the first `terraform apply` — not guidelines.

## Step 0 — Governance Relationship

- [ ] Meeting scheduled with governance team before writing resource blocks
- [ ] Shared Responsibility Matrix obtained (ROSA / ARO / OSD)
- [ ] Exception justification package prepared (survives reviewer rotation)
- [ ] Each required permission mapped to specific policy it satisfies
- [ ] Sandbox demonstration planned for highest-risk permissions (EC2/IAM, VM/roles, Compute/IAM SA)

## Platform-Specific Prerequisites

### ROSA (AWS)

- [ ] Marketplace SCP approved (separate high-risk track)
- [ ] Instance type capacity confirmed in mandated region (not just quota)
- [ ] Shared VPC / networking permissions validated with networking team
- [ ] STS assumed-role trust policy confirmed across all account boundaries
- [ ] Remote state backend provisioned with **versioning enabled** (verify explicitly)

### ARO (Azure)

- [ ] Azure Policy exceptions documented
- [ ] Subscription RBAC scoped and approved
- [ ] Entra ID app registration requirements understood
- [ ] Private endpoint for state storage (if no public egress)
- [ ] Remote state backend provisioned with **versioning and soft delete enabled**

### OSD (GCP)

- [ ] Org constraints and Workload Identity approval obtained
- [ ] Regional capacity confirmed
- [ ] Remote state backend provisioned with **object versioning enabled**

## Before Every Apply

- [ ] `terraform plan -out=tfplan` reviewed
- [ ] Saved plan shared with governance (if permission-related)
- [ ] After any failed apply: state audit before fix-and-retry

## Governance Questions to Answer

Every governance team will ask:

1. How does a third-party vendor access our private network and cloud account?
2. What is the precise scope of the IAM permissions being requested?
3. Who controls the trust relationships between the managed service and our account?
4. What happens to those permissions when the cluster is decommissioned?

The Shared Responsibility Matrix is the artifact that answers these most effectively.
