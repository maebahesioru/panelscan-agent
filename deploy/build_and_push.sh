#!/usr/bin/env bash
# Build the arm64 (Graviton) image and push it to ECR.
# Preconditions: awscli v2 configured, docker buildx with a working arm64 builder.
# This script was authored but NOT executed in this entry: no AWS account is attached
# to the submission. Running it is the human hand-over step.
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-northeast-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?set AWS_ACCOUNT_ID}"
REPO_NAME="${REPO_NAME:-panelscan-agent}"
TAG="${TAG:-$(date -u +%Y%m%d-%H%M%S)}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}:${TAG}"

echo "==> ensuring ECR repository ${REPO_NAME}"
aws ecr describe-repositories --repository-names "${REPO_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1 ||
  aws ecr create-repository --repository-name "${REPO_NAME}" --region "${AWS_REGION}" >/dev/null

echo "==> docker login"
aws ecr get-login-password --region "${AWS_REGION}" |
  docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> buildx build (linux/arm64) -> ${IMAGE}"
docker buildx build \
  --platform linux/arm64 \
  -f "${ROOT}/deploy/Dockerfile" \
  -t "${IMAGE}" \
  --push \
  "${ROOT}"

echo "==> pushed ${IMAGE}"
echo "next: update deploy/ecs-taskdef.json image field with ${IMAGE}"
