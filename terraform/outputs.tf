output "vpc_id" {
  value = module.network.vpc_id
}

output "cluster_name" {
  value = module.kubernetes.cluster_name
}

output "db_endpoint" {
  value = module.database.endpoint
}

output "db_master_secret_arn" {
  description = "ARN secret di AWS Secrets Manager yang berisi password database (dibuat otomatis, tidak ada di kode)."
  value       = module.database.master_secret_arn
}
