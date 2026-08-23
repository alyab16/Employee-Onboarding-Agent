project_name = "onboarding"
environment  = "prod"

# A stronger model for prod. The supervisor picks routes through structured
# output and the specialists work against 20 tool schemas, so verify any change
# with `python -m evals.run_evals` before it ships — the 15-case harness fails
# the build on routing and forbidden-tool regressions.
bedrock_model_id       = "us.amazon.nova-pro-v1:0"
bedrock_embed_model_id = "amazon.titan-embed-text-v2:0"
max_tokens             = 4096
auto_approve_seconds   = 30

lambda_memory_mb            = 3008
lambda_timeout              = 300
lambda_ephemeral_storage_mb = 1024
lambda_reserved_concurrency = 5
log_retention_days          = 30

enable_warmer           = true
warmer_interval_minutes = 5

use_custom_domain = false
root_domain       = ""
