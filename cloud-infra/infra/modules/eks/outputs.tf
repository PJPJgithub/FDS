output "cluster_endpoint" {
  description = "EKS API 서버 주소"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "EKS 클러스터 보안 그룹 ID"
  value       = module.eks.cluster_security_group_id
}

output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = module.eks.cluster_name
}
