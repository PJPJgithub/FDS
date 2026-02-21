module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.30"

  vpc_id     = var.vpc_id
  subnet_ids = var.subnet_ids

  cluster_endpoint_public_access = true

  # [삭제됨] enable_cluster_creator_admin_permissions = true 

  # [추가됨] v19용 권한 설정 (자동으로 내 사용자에게 관리자 권한 부여)
  # aws-auth는 나중에 수동으로 처리 (Terraform에서 관리 안 함)
  #manage_aws_auth_configmap = true
  #aws_auth_roles = [
    # 나중에 Worker Node가 붙을 수 있게 허용하는 설정 (필수!)
  #  {
  #    rolearn  = module.eks.eks_managed_node_groups["general"].iam_role_arn
  #    username = "system:node:{{EC2PrivateDNSName}}"
  #    groups   = ["system:bootstrappers", "system:nodes"]
  #  }
  #]
  
  # 내 현재 사용자(admin-user)를 관리자로 추가
  enable_irsa = true

  eks_managed_node_groups = {
    general = {
      name = "node-group-1"
      instance_types = ["t3.medium"]

      min_size     = 1
      max_size     = 3
      desired_size = 2

      capacity_type = "SPOT"
    }
  }

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}
