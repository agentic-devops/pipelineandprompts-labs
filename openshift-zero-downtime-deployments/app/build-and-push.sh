#!/bin/bash
# Build and push blue and green images to external registry (quay.io, Docker Hub, etc.)
#
# This script is for EXTERNAL registry deployment.
# For OpenShift internal registry, use oc new-build instead (see docs/prerequisites.md)
#
# Prerequisites:
#   - podman or docker installed
#   - logged into your registry: podman login quay.io
#   - run from the app/ directory
#
# Usage:
#   1. Edit REGISTRY variable below to your registry
#   2. Run: ./build-and-push.sh
#   3. Update manifests/*/deployment.yaml to use your registry

set -euo pipefail

# ⚠️ CHANGE THIS to your registry
REGISTRY="quay.io/YOUR-USERNAME"
IMAGE_NAME="nodejs-zero-downtime"

echo "NOTE: Using registry: ${REGISTRY}"
echo "      If this is incorrect, edit REGISTRY variable in this script"
echo ""

echo "==> Building blue image..."
podman build \
  --build-arg DEPLOYMENT_COLOUR=blue \
  -t ${REGISTRY}/${IMAGE_NAME}:blue \
  .

echo "==> Building green image..."
podman build \
  --build-arg DEPLOYMENT_COLOUR=green \
  -t ${REGISTRY}/${IMAGE_NAME}:green \
  .

echo "==> Pushing blue image..."
podman push ${REGISTRY}/${IMAGE_NAME}:blue

echo "==> Pushing green image..."
podman push ${REGISTRY}/${IMAGE_NAME}:green

echo ""
echo "==> Done. Images available at:"
echo "    ${REGISTRY}/${IMAGE_NAME}:blue"
echo "    ${REGISTRY}/${IMAGE_NAME}:green"
echo ""
echo "Next steps:"
echo "  1. Update manifests/blue/deployment.yaml image: ${REGISTRY}/${IMAGE_NAME}:blue"
echo "  2. Update manifests/green/deployment.yaml image: ${REGISTRY}/${IMAGE_NAME}:green"
echo "  3. Apply the manifests: oc apply -f manifests/"
echo ""
echo "Alternative: Use OpenShift internal registry (no external account needed)"
echo "  See docs/prerequisites.md Section 2 Option A for oc new-build approach"
