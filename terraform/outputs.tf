output "api_url" {
  description = "Lambda Function URL. Baked into the frontend bundle as NEXT_PUBLIC_API_URL."
  value       = aws_lambda_function_url.api.function_url
}

output "cloudfront_url" {
  description = "Public site URL"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "Used by the pipeline to invalidate the cache after an upload"
  value       = aws_cloudfront_distribution.main.id
}

output "custom_domain_url" {
  description = "Custom domain, when use_custom_domain is set"
  value       = var.use_custom_domain ? "https://${var.root_domain}" : ""
}

output "frontend_bucket" {
  description = "S3 bucket the static export is synced into"
  value       = aws_s3_bucket.frontend.id
}

output "ecr_repository_url" {
  description = "Registry the backend image is pushed to"
  value       = aws_ecr_repository.backend.repository_url
}

output "checkpoint_table" {
  description = "DynamoDB table holding LangGraph conversation state"
  value       = aws_dynamodb_table.checkpoints.name
}

output "lambda_function_name" {
  description = "Backend function name, for `aws logs tail`"
  value       = aws_lambda_function.api.function_name
}
