output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "kinesis_stream_name" {
  description = "Kinesis Stream Name"
  value       = aws_kinesis_stream.paysim_stream.name
}

output "kinesis_stream_arn" {
  description = "Kinesis Stream ARN"
  value       = aws_kinesis_stream.paysim_stream.arn
}
