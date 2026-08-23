#!/usr/bin/env bash
#
# Tear down one environment.
#
#   ./scripts/destroy.sh <dev|test|prod> [project_name]
#
# THIS DELETES DATA. The DynamoDB checkpoint table goes with the stack, and it
# holds every conversation and every pending approval for the environment.
#
# Two things make `terraform destroy` fail on this stack if they are not handled
# first; both are dealt with below rather than left for the operator:
#
#   - A non-empty S3 bucket. force_destroy is set on the frontend bucket, but
#     emptying it first keeps the destroy from timing out on a large sync.
#   - A registry that still holds images. force_delete is set on the ECR repo
#     for the same reason.

set -euo pipefail

ENVIRONMENT="${1:-}"
PROJECT_NAME="${2:-onboarding}"

if [[ ! "${ENVIRONMENT}" =~ ^(dev|test|prod)$ ]]; then
  echo "Usage: $0 <dev|test|prod> [project_name]" >&2
  exit 1
fi

REGION="${DEFAULT_AWS_REGION:-${AWS_REGION:-us-east-1}}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}/terraform"

STATE_BUCKET="${PROJECT_NAME}-terraform-state-${ACCOUNT_ID}"
LOCK_TABLE="${PROJECT_NAME}-terraform-locks"

TF_VARS=(-var "project_name=${PROJECT_NAME}" -var "environment=${ENVIRONMENT}")
if [ "${ENVIRONMENT}" = "prod" ]; then
  TF_VARS+=(-var-file=prod.tfvars)
fi

echo "==> terraform init"
terraform init -reconfigure -input=false \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="key=${ENVIRONMENT}/terraform.tfstate" \
  -backend-config="region=${REGION}" \
  -backend-config="dynamodb_table=${LOCK_TABLE}" \
  -backend-config="encrypt=true"

if ! terraform workspace select "${ENVIRONMENT}" 2>/dev/null; then
  echo "No workspace '${ENVIRONMENT}' — nothing to destroy."
  exit 0
fi

# Empty the frontend bucket first. `|| true` because a stack that failed
# halfway may not have a bucket to read.
FRONTEND_BUCKET="$(terraform output -raw frontend_bucket 2>/dev/null || echo '')"
if [ -n "${FRONTEND_BUCKET}" ]; then
  echo "==> Emptying s3://${FRONTEND_BUCKET}"
  aws s3 rm "s3://${FRONTEND_BUCKET}" --recursive || true
fi

echo "==> terraform destroy"
terraform destroy -auto-approve -input=false "${TF_VARS[@]}"

echo
echo "Destroyed ${PROJECT_NAME}-${ENVIRONMENT}."
echo "The Terraform state bucket and lock table are account-level and were left in place."
echo "Remove the workspace too if you are done with the environment:"
echo "  terraform workspace select default && terraform workspace delete ${ENVIRONMENT}"
