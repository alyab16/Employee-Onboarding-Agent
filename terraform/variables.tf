variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "onboarding"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment name (dev, test, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, prod."
  }
}

variable "image_tag" {
  description = "ECR image tag to deploy. scripts/deploy.sh passes the git SHA so every commit is a distinct, rollback-able image."
  type        = string
  default     = "latest"
}

# --- Model configuration --------------------------------------------------

variable "bedrock_model_id" {
  description = <<-EOT
    Bedrock model (or inference profile) ID for the supervisor and specialists.
    Cross-region inference profiles need a region prefix, e.g. "us.".
    Verify the ID in the Bedrock console — model IDs change more often than this stack does.
    Run `python -m evals.run_evals` against a candidate before switching: the
    supervisor relies on structured output and the specialists on 20 tool schemas,
    and smaller models degrade on both before they degrade on prose.
  EOT
  type        = string
  default     = "us.amazon.nova-lite-v1:0"
}

variable "bedrock_embed_model_id" {
  description = "Bedrock embedding model for the RAG index. Changing this invalidates the Chroma index automatically (the doc hash includes the provider string)."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "max_tokens" {
  description = "Max output tokens per model call"
  type        = number
  default     = 4096
}

variable "auto_approve_seconds" {
  description = "Seconds before the simulated manager auto-approves an access request"
  type        = number
  default     = 30
}

# --- Lambda sizing --------------------------------------------------------

variable "lambda_memory_mb" {
  description = <<-EOT
    Lambda memory. CPU scales with it, so this also sets cold-start speed.
    The process tree is uvicorn plus five FastMCP stdio subprocesses, each
    importing LangChain — 1024 MB is not enough. Measure locally with
    `docker stats` before lowering.
  EOT
  type        = number
  default     = 2048
}

variable "lambda_timeout" {
  description = "Function timeout in seconds. Must exceed cold-start boot (~60-90s: MCP spawn, tool discovery, vector index build) plus one full agent turn."
  type        = number
  default     = 300
}

variable "lambda_ephemeral_storage_mb" {
  description = "Size of /tmp. Holds the seeded SQLite file, the Chroma index and the BM25 pickle, all rebuilt per cold start."
  type        = number
  default     = 1024
}

variable "lambda_reserved_concurrency" {
  description = <<-EOT
    Reserved concurrency. Doubles as the cost ceiling on an unauthenticated
    Function URL and as a bound on SQLite divergence: /tmp is per execution
    environment, so N concurrent environments means N independent copies of the
    mock HR data. Conversation state is unaffected — that lives in DynamoDB.
  EOT
  type        = number
  default     = 2
}

variable "log_retention_days" {
  description = "CloudWatch log retention"
  type        = number
  default     = 14
}

# --- Cold-start warmer ----------------------------------------------------

variable "enable_warmer" {
  description = <<-EOT
    Ping /health on a schedule to keep one execution environment alive.
    A cold start costs 60-90 seconds of silence on the first message, which is
    the single worst thing about this deployment; the pings cost a few cents a
    month. Verify the synthetic event in main.tf actually reaches the adapter
    before trusting it — check for GET /health lines in CloudWatch.
  EOT
  type        = bool
  default     = true
}

variable "warmer_interval_minutes" {
  description = "Minutes between warmer pings. Lambda keeps an idle environment for roughly 5-15 minutes."
  type        = number
  default     = 5
}

# --- Optional custom domain ----------------------------------------------

variable "use_custom_domain" {
  description = "Attach a custom domain to the CloudFront distribution"
  type        = bool
  default     = false
}

variable "root_domain" {
  description = "Apex domain, e.g. example.com. Requires an existing Route 53 hosted zone."
  type        = string
  default     = ""
}
