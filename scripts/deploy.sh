#!/usr/bin/env bash
#
# Deploy the Employee Onboarding Agent.
#
#   ./scripts/deploy.sh <dev|test|prod> [project_name]
#
# Requires: aws cli, terraform >= 1.5, docker, node 24, and credentials for the
# target account. Run scripts/bootstrap.sh once before the first deploy.
#
# Ordering here is not arbitrary:
#
#   1. ECR must exist before an image can be pushed.
#   2. The image must exist before Lambda can reference it — a container
#      function fails to create against a missing image URI.
#   3. The Function URL must exist before the frontend builds, because
#      NEXT_PUBLIC_API_URL is compiled into the static bundle rather than read
#      at runtime.
#
# That is why the stack is applied in two passes with a docker push in between.

set -euo pipefail

ENVIRONMENT="${1:-}"
PROJECT_NAME="${2:-onboarding}"

if [[ ! "${ENVIRONMENT}" =~ ^(dev|test|prod)$ ]]; then
  echo "Usage: $0 <dev|test|prod> [project_name]" >&2
  exit 1
fi

REGION="${DEFAULT_AWS_REGION:-${AWS_REGION:-us-east-1}}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo manual-$(date +%s))}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

STATE_BUCKET="${PROJECT_NAME}-terraform-state-${ACCOUNT_ID}"
LOCK_TABLE="${PROJECT_NAME}-terraform-locks"

TF_VARS=(-var "project_name=${PROJECT_NAME}" -var "environment=${ENVIRONMENT}" -var "image_tag=${IMAGE_TAG}")
if [ "${ENVIRONMENT}" = "prod" ]; then
  TF_VARS+=(-var-file=prod.tfvars)
fi

echo "==> Environment ${ENVIRONMENT} | region ${REGION} | image tag ${IMAGE_TAG}"

# --- 1. Terraform init ----------------------------------------------------
echo "==> terraform init"
cd terraform
terraform init -reconfigure -input=false \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="key=${ENVIRONMENT}/terraform.tfstate" \
  -backend-config="region=${REGION}" \
  -backend-config="dynamodb_table=${LOCK_TABLE}" \
  -backend-config="encrypt=true"

terraform workspace select "${ENVIRONMENT}" 2>/dev/null || terraform workspace new "${ENVIRONMENT}"

# --- 2. Create the registry first ----------------------------------------
echo "==> terraform apply (registry only)"
terraform apply -auto-approve -input=false "${TF_VARS[@]}" \
  -target=aws_ecr_repository.backend \
  -target=aws_ecr_lifecycle_policy.backend

ECR_URL="$(terraform output -raw ecr_repository_url)"
cd "${REPO_ROOT}"

# --- 3. Build and push the backend image ---------------------------------
echo "==> docker build -> ${ECR_URL}:${IMAGE_TAG}"
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ECR_URL%%/*}"

# linux/amd64 explicitly: Lambda will not run an arm64 image built by default
# on an Apple Silicon machine, and the failure surfaces as a runtime error
# rather than a build one.
docker build --platform linux/amd64 \
  -f backend/Dockerfile.lambda \
  -t "${ECR_URL}:${IMAGE_TAG}" \
  -t "${ECR_URL}:latest" \
  backend

docker push "${ECR_URL}:${IMAGE_TAG}"
docker push "${ECR_URL}:latest"

# --- 4. Apply the rest of the stack --------------------------------------
echo "==> terraform apply (full stack)"
cd terraform
terraform apply -auto-approve -input=false "${TF_VARS[@]}"

API_URL="$(terraform output -raw api_url)"
SITE_URL="$(terraform output -raw cloudfront_url)"
BUCKET="$(terraform output -raw frontend_bucket)"
DISTRIBUTION_ID="$(terraform output -raw cloudfront_distribution_id)"
CUSTOM_URL="$(terraform output -raw custom_domain_url)"
cd "${REPO_ROOT}"

# --- 5. Build and publish the frontend -----------------------------------
# NEXT_OUTPUT=export flips next.config.ts from the standalone server build
# (what docker-compose uses) to a static export in ./out.
echo "==> npm run build (static export)"
cd frontend
printf 'NEXT_PUBLIC_API_URL=%s\n' "${API_URL%/}" > .env.production
npm ci --no-audit --no-fund
NEXT_OUTPUT=export npm run build

if [ ! -d out ]; then
  echo "ERROR: frontend/out was not produced despite NEXT_OUTPUT=export." >&2
  echo "Check that next.config.ts still honours the NEXT_OUTPUT switch." >&2
  exit 1
fi

aws s3 sync ./out "s3://${BUCKET}/" --delete
cd "${REPO_ROOT}"

# --- 6. Invalidate the cache ---------------------------------------------
echo "==> CloudFront invalidation"
aws cloudfront create-invalidation \
  --distribution-id "${DISTRIBUTION_ID}" \
  --paths "/*" >/dev/null

cat <<EOF

Deployed ${PROJECT_NAME}-${ENVIRONMENT}

  Site   ${SITE_URL}
  ${CUSTOM_URL:+Domain ${CUSTOM_URL}}
  API    ${API_URL}
  Image  ${IMAGE_TAG}

The first request after a deploy is a cold start — roughly 60-90 seconds while
the MCP subprocesses spawn and the vector index rebuilds. Confirm streaming
works end to end before declaring victory:

  curl -N -X POST "${API_URL%/}/api/chat" \\
    -H 'Content-Type: application/json' \\
    -d '{"employee_id":"emp001","message":"What is our PTO policy?"}'

Deltas should arrive progressively. If the whole body lands at once, the
Function URL is not in RESPONSE_STREAM mode or AWS_LWA_INVOKE_MODE is unset.
EOF
