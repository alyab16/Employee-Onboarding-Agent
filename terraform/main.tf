#############################################################################
# Employee Onboarding Agent — serverless stack
#
#   Browser ──HTTPS──> CloudFront ──OAC──> S3   (Next.js static export)
#          └──HTTPS──> Lambda Function URL     (FastAPI + LangGraph, streaming)
#                          ├──> Bedrock        (chat + embeddings, via IAM)
#                          └──> DynamoDB       (LangGraph checkpoints)
#
# The browser calls the Function URL directly rather than through CloudFront.
# That is deliberate: CloudFront OAC signs origin requests with SigV4, and a
# signed POST body plus a streaming response is the one combination most likely
# to fail in a way that is hard to debug. Keeping the API on its own origin
# costs a CORS config and buys a much shorter list of things that can break.
#############################################################################

data "aws_caller_identity" "current" {}

locals {
  prefix       = "${var.project_name}-${var.environment}"
  account_id   = data.aws_caller_identity.current.account_id
  cors_origins = var.use_custom_domain ? "https://${var.root_domain},https://www.${var.root_domain}" : "https://${aws_cloudfront_distribution.main.domain_name}"
}

#############################################################################
# Container registry
#############################################################################

resource "aws_ecr_repository" "backend" {
  name                 = "${local.prefix}-backend"
  image_tag_mutability = "MUTABLE"

  # Without this, `terraform destroy` fails on a repository that still holds
  # images — which it always will, because the deploy pushed one.
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 5 most recent images; the backend image is ~2 GB."
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

#############################################################################
# Conversation state
#
# This table is what makes the whole serverless design possible. With the
# in-process MemorySaver, /api/chat and /api/chat/resume had to hit the same
# process, which ruled out Lambda entirely. DynamoDBSaver moves graph state —
# including a paused HITL interrupt — out of the process, so an approval can be
# answered by a different execution environment minutes later.
#############################################################################

resource "aws_dynamodb_table" "checkpoints" {
  name         = "${local.prefix}-checkpoints"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.environment == "prod"
  }
}

#############################################################################
# IAM
#############################################################################

resource "aws_iam_role" "lambda" {
  name = "${local.prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_inline" {
  name = "${local.prefix}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Checkpoints"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
        ]
        Resource = aws_dynamodb_table.checkpoints.arn
      },
      {
        Sid    = "BedrockInference"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        # Foundation models are account-less ARNs; inference profiles are not.
        # A cross-region profile ID needs both entries to resolve.
        Resource = [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:*:${local.account_id}:inference-profile/*",
        ]
      },
    ]
  })
}

#############################################################################
# Backend — Lambda container image behind a streaming Function URL
#############################################################################

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.prefix}-api"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "api" {
  function_name = "${local.prefix}-api"
  role          = aws_iam_role.lambda.arn

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"

  memory_size                    = var.lambda_memory_mb
  timeout                        = var.lambda_timeout
  reserved_concurrent_executions = var.lambda_reserved_concurrency

  ephemeral_storage {
    size = var.lambda_ephemeral_storage_mb
  }

  environment {
    variables = {
      # Model plane — no API key anywhere; the role above is the credential.
      BEDROCK_MODEL_ID       = var.bedrock_model_id
      BEDROCK_EMBED_MODEL_ID = var.bedrock_embed_model_id
      MAX_TOKENS             = tostring(var.max_tokens)
      AUTO_APPROVE_SECONDS   = tostring(var.auto_approve_seconds)

      # Presence of this variable is what switches orchestrator.py from
      # MemorySaver to DynamoDBSaver.
      CHECKPOINT_TABLE = aws_dynamodb_table.checkpoints.name

      # The browser calls the Function URL cross-origin, so FastAPI's
      # CORSMiddleware has to allow the CloudFront domain explicitly —
      # allow_credentials=True in main.py makes a wildcard illegal.
      CORS_ORIGINS = local.cors_origins
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda_inline,
  ]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"

  # Without RESPONSE_STREAM the adapter buffers the whole SSE body and the UI
  # renders one lump of text at the end of the turn instead of live deltas.
  invoke_mode = "RESPONSE_STREAM"
}

#############################################################################
# Cold-start warmer
#
# A cold start replays the whole lifespan: spawn five MCP subprocesses,
# discover 18 tools, re-embed 7 policy documents, re-seed SQLite. That is
# 60-90 seconds of silence on the first message. One ping every few minutes
# keeps an environment resident for a few cents a month.
#
# The payload is a synthetic Function URL (API Gateway v2) event, which is the
# shape the Web Adapter translates into an HTTP request. Confirm you see
# `GET /health` in CloudWatch after the first tick; if not, set
# enable_warmer = false rather than leaving a silently useless rule in place.
#############################################################################

resource "aws_cloudwatch_event_rule" "warmer" {
  count = var.enable_warmer ? 1 : 0

  name                = "${local.prefix}-warmer"
  description         = "Keep one Lambda execution environment warm"
  schedule_expression = "rate(${var.warmer_interval_minutes} minutes)"
}

resource "aws_cloudwatch_event_target" "warmer" {
  count = var.enable_warmer ? 1 : 0

  rule      = aws_cloudwatch_event_rule.warmer[0].name
  target_id = "lambda"
  arn       = aws_lambda_function.api.arn

  input = jsonencode({
    version = "2.0"
    rawPath = "/health"
    headers = { "x-warmer" = "true" }
    requestContext = {
      http = {
        method    = "GET"
        path      = "/health"
        protocol  = "HTTP/1.1"
        sourceIp  = "127.0.0.1"
        userAgent = "eventbridge-warmer"
      }
    }
    isBase64Encoded = false
  })
}

resource "aws_lambda_permission" "warmer" {
  count = var.enable_warmer ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.warmer[0].arn
}

#############################################################################
# Frontend — static export in a private bucket, served through CloudFront
#############################################################################

resource "aws_s3_bucket" "frontend" {
  bucket        = "${local.prefix}-frontend-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${local.prefix}-frontend-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${local.prefix} frontend"
  price_class         = "PriceClass_100"

  aliases = var.use_custom_domain ? [var.root_domain, "www.${var.root_domain}"] : []

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # AWS managed policy: CachingOptimized
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  # A static export has no server to resolve unknown paths, so hand every miss
  # back to the SPA shell and let the client router decide.
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.use_custom_domain ? false : true
    acm_certificate_arn            = var.use_custom_domain ? aws_acm_certificate_validation.site[0].certificate_arn : null
    ssl_support_method             = var.use_custom_domain ? "sni-only" : null
    minimum_protocol_version       = var.use_custom_domain ? "TLSv1.2_2021" : null
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.main.arn
        }
      }
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

#############################################################################
# Optional custom domain
#############################################################################

data "aws_route53_zone" "main" {
  count = var.use_custom_domain ? 1 : 0

  name         = var.root_domain
  private_zone = false
}

resource "aws_acm_certificate" "site" {
  count    = var.use_custom_domain ? 1 : 0
  provider = aws.us_east_1

  domain_name               = var.root_domain
  subject_alternative_names = ["www.${var.root_domain}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = var.use_custom_domain ? {
    for dvo in aws_acm_certificate.site[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  zone_id         = data.aws_route53_zone.main[0].zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "site" {
  count    = var.use_custom_domain ? 1 : 0
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

resource "aws_route53_record" "alias_apex" {
  count = var.use_custom_domain ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.root_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "alias_www" {
  count = var.use_custom_domain ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "www.${var.root_domain}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}
