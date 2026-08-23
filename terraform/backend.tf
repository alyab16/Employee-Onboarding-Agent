# Remote state. Every setting is supplied by `terraform init -backend-config=...`
# from scripts/deploy.sh, so the bucket name can carry the account ID without
# being hardcoded here.
#
# The bucket and lock table are NOT managed by this stack — they must exist
# before the first init, or Terraform would be storing the state that describes
# them inside themselves. Run scripts/bootstrap.sh once per account.
terraform {
  backend "s3" {}
}
