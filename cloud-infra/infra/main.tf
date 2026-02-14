# 1. VPC 구성 (EKS를 위해 넉넉하게 잡습니다)
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "fraud-detection-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["ap-northeast-2a", "ap-northeast-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"] # EKS 노드용 (외부 접근 차단)
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"] # 로드밸런서, NAT용

  enable_nat_gateway = true
  single_nat_gateway = true  # 비용 절약: NAT Gateway를 하나만 씁니다! (중요)
  enable_dns_hostnames = true

  # EKS가 VPC를 잘 찾도록 태그 설정 (필수)
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

# 2. Kinesis Data Stream (데이터 파이프)
resource "aws_kinesis_stream" "paysim_stream" {
  name             = "paysim-stream"
  shard_count      = 1             # 비용 절약: 샤드 1개 (1MB/sec 처리 가능)
  retention_period = 24            # 데이터 보관 24시간

  shard_level_metrics = [
    "IncomingBytes",
    "OutgoingBytes"
  ]
}
