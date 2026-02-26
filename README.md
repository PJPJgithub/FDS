# FDS

# 🛡️ Real-time Financial Fraud Detection System on AWS EKS

> **PaySim 데이터를 활용한 실시간 금융 이상 거래 탐지 및 자동 차단 시스템**  
> **AWS EKS, Kinesis, Serverless 아키텍처 기반의 고가용성 파이프라인 구축**

![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=for-the-badge&logo=kubernetes&logoColor=white)
![Terraform](https://img.shields.io/badge/terraform-%235835CC.svg?style=for-the-badge&logo=terraform&logoColor=white)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

---

## 📖 Project Overview
금융 거래 데이터(PaySim)가 실시간으로 유입되는 환경을 가정하여, **이상 거래(Fraud)를 0.1초 이내에 탐지하고 즉시 보안 조치(계좌 동결 및 알림)**를 수행하는 시스템입니다.  
클라우드 네이티브 환경인 **AWS EKS(Kubernetes)** 위에서 운영되며, 트래픽 폭주 상황에 대비해 **KEDA를 활용한 이벤트 기반 오토스케일링**이 적용되어 있습니다.


### 📊 Data & Modeling Overview
본 프로젝트는 PaySim 모바일 금융 거래 시뮬레이션 데이터를 활용하여 실시간 금융 사기 거래 탐지를 수행한다.

해당 데이터는 약 600만 건의 거래 중 사기 거래 비율이 극히 낮은 심각한 클래스 불균형을 가지며, 일부 변수는 데이터 설명과 실제 값 간의 불일치 가능성이 존재한다.

이에 따라 본 프로젝트에서는 탐색적 데이터 분석(EDA)을 통해
데이터 특성을 면밀히 검토하고, 특징 공학을 기반으로 실제 환경에 적용 가능한 사기 탐지 모델을 설계한다.

### 👥 Team & Role
*   **자라🐢 (Cloud Engineer):** 인프라 아키텍처 설계, EKS 구축, CI/CD 파이프라인, 모니터링 시스템 구현
*   **히새🐥 (Data Scientist):** PaySim 데이터 분석, 이상 탐지 머신러닝 모델 개발

---

## 🏗️ Architecture
**"Event-Driven & Scalable"**

1.  **Ingestion:** Python Generator가 초당 10~100건의 금융 거래 데이터를 생성하여 **Amazon Kinesis**로 전송
2.  **Processing:** **AWS EKS** 상의 Consumer Pod가 실시간으로 데이터를 Polling하여 AI 모델 추론 수행
3.  **Action:**
    *   **Fraud:** 즉시 **DynamoDB** BlockList에 등록하고 **AWS SNS**를 통해 관리자에게 경고 발송
    *   **Normal:** 거래 로그 저장
+  **Autoscaling:** **KEDA**가 Kinesis의 Lag(지연)를 감지하여 트래픽 증가 시 Pod를 자동으로 확장 (HPA)

*(아키텍처 다이어그램 이미지*

---

## 🛠️ Tech Stack

| Category | Technology | Usage |
| :--- | :--- | :--- |
| **Infra & IaC** | **Terraform** | VPC, EKS, Kinesis, DB 등 전 리소스 코드화 및 배포 자동화 |
| **Container** | **AWS EKS (K8s)** | 고가용성 마이크로서비스 운영 및 오케스트레이션 |
| **Stream** | **Amazon Kinesis** | 대용량 트랜잭션 데이터 버퍼링 및 스트리밍 처리 |
| **Scaling** | **KEDA** | 스트림 데이터양(Lag) 기반의 Event-driven Autoscaling 구현 |
| **Database** | **Amazon DynamoDB** | 이상 거래 유저 정보 및 차단 리스트 관리 (NoSQL) |
| **Security** | **IAM (IRSA)** | Pod 단위의 세밀한 권한 제어 (Least Privilege) |
| **Language** | **Python 3.9** | 데이터 생성기 및 모델 추론 애플리케이션 개발 |

---

## 💰 Cost Optimization Strategy (DevOps Perspective)
클라우드 비용 효율성을 고려하여 다음과 같은 전략을 적용했습니다.

1.  **Spot Instances 활용:** EKS Node Group에 AWS Spot Instance를 적용하여 컴퓨팅 비용 **약 70% 절감**
2.  **Environment Isolation:** Terraform Workspace를 활용하여 Dev/Prod 환경 분리 및 리소스 수명 주기 관리
3.  **On-Demand Testing:** 로컬 개발 시에는 `DRY_RUN` 모드를 활용하여 불필요한 API 호출 비용 방지

---

## 🚀 How to Run (실행 가이드)

이 프로젝트를 로컬 및 AWS 환경에서 실행하는 순서입니다.

### **사전 준비**
```bash
# 1. AWS CLI + kubectl + terraform 설치
aws configure  # Access Key 입력
```

### **1. 인프라 구축** (15분)
```bash
cd infra
terraform init
terraform apply -auto-approve  # EKS + Kinesis + DynamoDB + SNS
aws eks update-kubeconfig --region ap-northeast-2 --name fraud-detection-cluster
```

### **2. K8s 배포** (2분)
```bash
kubectl apply -f k8s/serviceaccount.yaml  # IRSA
kubectl apply -f k8s/deployment.yaml      # ML Consumer
kubectl rollout status deployment/fraud-consumer-deployment
```

### **3. 데모 실행** (실시간 테스트)
```bash
# 터미널 1: 데이터 생성
cd ai-model
python generator.py

# 터미널 2: 실시간 로그 (✅🚨🚫 확인)
kubectl logs -f deployment/fraud-consumer-deployment
```

**예상 결과:**
```
✅ NORMAL: 5443.26
🚨 FRAUD DETECTED: 18498.8
🚫 BLOCKED: C123456789
```

## 🚀 How to Terminate (종료 가이드)

```bash
# 1. 데모 중지
# generator: Ctrl+C

# 2. K8s 리소스 삭제
kubectl delete deployment fraud-consumer-deployment
kubectl delete sa fraud-consumer-sa

# 3. 인프라 삭제 (비용 0원)
cd infra
terraform destroy -auto-approve

# 4. ECR 정리 (선택)
aws ecr delete-repository --repository-name fraud-consumer --region ap-northeast-2 --force
```

## 📊 **예상 비용 (크레딧 사용)**
```
EKS Control Plane: 무료 ($0.10/hr)
EC2 t3.micro x3: $0.05/hr
Kinesis/DynamoDB: $0.01/시간
```

## 🔍 **Troubleshooting**
```
❌ "deployment not found": terraform apply 재실행
❌ IRSA AccessDenied: IAM Trust Policy OIDC 확인
❌ DynamoDB Float 에러: Decimal(str(amount))
```