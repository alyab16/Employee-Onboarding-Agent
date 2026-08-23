#!/usr/bin/env bash
#
# One-time per-account bootstrap.
#
# Creates the two things Terraform cannot create for itself — the bucket and
# lock table that hold its own state — plus the IAM role GitHub Actions assumes
# through OIDC.
#
# Usage:
#   ./scripts/bootstrap.sh [github_org/repo] [project_name]
#
# Idempotent: every step checks before it creates.

set -euo pipefail

GITHUB_REPO="${1:-}"
PROJECT_NAME="${2:-onboarding}"
REGION="${DEFAULT_AWS_REGION:-${AWS_REGION:-us-east-1}}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
STATE_BUCKET="${PROJECT_NAME}-terraform-state-${ACCOUNT_ID}"
LOCK_TABLE="${PROJECT_NAME}-terraform-locks"
ROLE_NAME="${PROJECT_NAME}-github-actions"

echo "Account : ${ACCOUNT_ID}"
echo "Region  : ${REGION}"
echo "Bucket  : ${STATE_BUCKET}"
echo "Table   : ${LOCK_TABLE}"
echo

# --- State bucket ---------------------------------------------------------
if aws s3api head-bucket --bucket "${STATE_BUCKET}" 2>/dev/null; then
  echo "State bucket already exists — leaving it alone."
else
  echo "Creating state bucket..."
  if [ "${REGION}" = "us-east-1" ]; then
    # us-east-1 rejects a LocationConstraint, every other region requires one.
    aws s3api create-bucket --bucket "${STATE_BUCKET}" --region "${REGION}"
  else
    aws s3api create-bucket --bucket "${STATE_BUCKET}" --region "${REGION}" \
      --create-bucket-configuration "LocationConstraint=${REGION}"
  fi

  aws s3api put-bucket-versioning --bucket "${STATE_BUCKET}" \
    --versioning-configuration Status=Enabled

  aws s3api put-bucket-encryption --bucket "${STATE_BUCKET}" \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

  aws s3api put-public-access-block --bucket "${STATE_BUCKET}" \
    --public-access-block-configuration \
    'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
fi

# --- Lock table -----------------------------------------------------------
if aws dynamodb describe-table --table-name "${LOCK_TABLE}" >/dev/null 2>&1; then
  echo "Lock table already exists — leaving it alone."
else
  echo "Creating lock table..."
  aws dynamodb create-table \
    --table-name "${LOCK_TABLE}" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${REGION}" >/dev/null
  aws dynamodb wait table-exists --table-name "${LOCK_TABLE}" --region "${REGION}"
fi

# --- GitHub OIDC ----------------------------------------------------------
if [ -z "${GITHUB_REPO}" ]; then
  echo
  echo "No github_org/repo given — skipping the OIDC role."
  echo "Re-run as: ./scripts/bootstrap.sh your-org/your-repo"
  exit 0
fi

OIDC_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"

if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "${OIDC_ARN}" >/dev/null 2>&1; then
  echo "GitHub OIDC provider already registered."
else
  echo "Registering the GitHub OIDC provider..."
  aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 >/dev/null
fi

if aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
  echo "Role ${ROLE_NAME} already exists — leaving its policies alone."
else
  echo "Creating ${ROLE_NAME}..."
  TRUST_POLICY="$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "${OIDC_ARN}" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
      "StringLike": { "token.actions.githubusercontent.com:sub": "repo:${GITHUB_REPO}:*" }
    }
  }]
}
JSON
)"

  aws iam create-role --role-name "${ROLE_NAME}" \
    --assume-role-policy-document "${TRUST_POLICY}" >/dev/null

  # PowerUserAccess plus IAM is broad. It is the pragmatic starting point for a
  # stack that creates roles, and the first thing to tighten once the resource
  # list stops changing — scope it to the ARNs in terraform/main.tf.
  aws iam attach-role-policy --role-name "${ROLE_NAME}" \
    --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
  aws iam attach-role-policy --role-name "${ROLE_NAME}" \
    --policy-arn arn:aws:iam::aws:policy/IAMFullAccess
fi

cat <<EOF

Bootstrap complete.

Add these to the GitHub repository (Settings > Secrets and variables > Actions):

  AWS_ROLE_ARN        arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}
  AWS_ACCOUNT_ID      ${ACCOUNT_ID}
  DEFAULT_AWS_REGION  ${REGION}

One more manual step Terraform cannot do for you: enable access to the Bedrock
models in ${REGION} (Bedrock console > Model access). Without it the first
deploy succeeds and every chat turn fails with AccessDeniedException.
EOF
