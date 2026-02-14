terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"  # 서울 리전
  
  # 모든 리소스에 공통 태그를 답니다 (관리 용이성)
  default_tags {
    tags = {
      Project     = "FraudDetection"
      Environment = "Dev"
      Owner       = "MyName"
    }
  }
}
