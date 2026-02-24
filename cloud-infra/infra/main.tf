# 1. VPC 구성 (EKS를 위해 넉넉하게 잡습니다)
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"
  
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

# 3. EKS 클러스터 생성
module "eks_cluster" {
  source = "./modules/eks"

  cluster_name = "fraud-detection-cluster"
  vpc_id       = module.vpc.vpc_id
  
  # EKS 노드는 Private Subnet에 배치하는 것이 보안 원칙입니다!
  subnet_ids   = module.vpc.private_subnets
}

# 3-1. 거래 로그 테이블 (모든 거래 저장)
resource "aws_dynamodb_table" "transaction_logs" {
  name           = "transaction-logs"
  billing_mode   = "PAY_PER_REQUEST"  # 비용 절약 (쓰는 만큼만)
  hash_key       = "transaction_id"

  attribute {
    name = "transaction_id"
    type = "S"
  }

  tags = {
    Name = "FraudDetection-TransactionLogs"
  }
}

# 3-2. 차단 리스트 테이블 (Fraud 유저 저장)
resource "aws_dynamodb_table" "block_list" {
  name           = "block-list"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  ttl {
    attribute_name = "ttl"  # 자동 삭제 (보안상 오래된 차단 정보는 삭제)
    enabled        = true
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  tags = {
    Name = "FraudDetection-BlockList"
  }
}