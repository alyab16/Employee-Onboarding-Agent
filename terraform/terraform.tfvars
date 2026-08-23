# Defaults for dev and test. prod.tfvars overrides for prod.
project_name = "onboarding"
environment  = "dev"

bedrock_model_id       = "us.amazon.nova-lite-v1:0"
bedrock_embed_model_id = "amazon.titan-embed-text-v2:0"
max_tokens             = 4096
auto_approve_seconds   = 30

lambda_memory_mb            = 2048
lambda_timeout              = 300
lambda_ephemeral_storage_mb = 1024
lambda_reserved_concurrency = -1
log_retention_days          = 14

enable_warmer           = true
warmer_interval_minutes = 5

use_custom_domain = false
root_domain       = ""
