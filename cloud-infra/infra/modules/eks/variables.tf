variable "cluster_name" {
  description = "EKS 클러스터 이름"
  type        = string
}

variable "vpc_id" {
  description = "EKS가 설치될 VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "EKS 노드가 배치될 서브넷 ID 목록"
  type        = list(string)
}
