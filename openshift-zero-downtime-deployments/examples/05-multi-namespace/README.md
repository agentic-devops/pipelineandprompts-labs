# Example 05 — Multi-Namespace Variant

## What this does

Adapts the blue/green pattern for multi-tenant clusters where
blue and green deployments run in separate namespaces. Uses
ExternalName services to bridge the HAProxy Route in a central
namespace to deployments in dedicated namespaces.

This pattern is common in enterprise OpenShift environments where:
- Teams have dedicated namespaces with their own quotas and RBAC
- A platform team manages routing in a shared ingress namespace
- Compliance requirements mandate namespace isolation between
  environments

## Architecture
