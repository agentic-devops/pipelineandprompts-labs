#!/bin/bash
# Build and push blue and green images to quay.io/flyers22
# Run this once before triggering the pipeline for the first time
#
# Prerequisites:
#   - podman or docker installed
#   - logged into quay.io: podman login quay.io
#   - run from the app/ directory

set -euo pipefail

REGISTRY="quay.io/flyers22"
IMAGE_NAME="nodejs-zero-downtime"

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
echo "Next step: apply the manifests and run the pipeline."
