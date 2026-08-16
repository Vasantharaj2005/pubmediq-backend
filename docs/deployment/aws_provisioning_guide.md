# ☁️ AWS Manual Provisioning Guide (Console)

This guide walks you through setting up the infrastructure for the PubMedIQ backend using the AWS Console. Since you approved the deployment architecture, follow these steps to configure your AWS environment to host the ECS Fargate cluster, PostgreSQL Database, and Redis Cache.

---

## 1. 🗄️ Database Setup (Amazon RDS)

We will use Amazon RDS for PostgreSQL.
1. Navigate to **Amazon RDS** in the AWS Console.
2. Click **Create database**.
3. Choose **Standard create** and **PostgreSQL** engine.
4. Select **Free tier** or **Dev/Test** depending on your budget.
5. **Settings**:
   - DB instance identifier: `pubmediq-db`
   - Master username: `postgres`
   - Master password: `<YOUR_SECURE_PASSWORD>` (Save this!)
6. **Connectivity**:
   - VPC: Default VPC.
   - Public access: **No** (ECS will communicate with it privately).
   - VPC security group: Create a new security group named `pubmediq-db-sg`.
7. Click **Create database**.

---

## 2. ⚡ Cache Setup (Amazon ElastiCache for Redis)

1. Navigate to **Amazon ElastiCache** > **Redis clusters**.
2. Click **Create Redis cluster**.
3. Choose **Design your own cache** -> **Cluster mode Disabled**.
4. Name: `pubmediq-redis`.
5. Instance size: `cache.t4g.micro` (cheapest for dev) or higher.
6. Under **Subnet group**, create one using the default VPC.
7. Under **Security**, choose the same security group or a dedicated one (`pubmediq-redis-sg`) that allows inbound port `6379`.
8. Click **Create**.

---

## 3. 🛡️ Networking & Security Groups

Before creating the ECS cluster, ensure your security groups allow traffic:

1. Go to **EC2** > **Security Groups**.
2. Find your **DB Security Group** (`pubmediq-db-sg`) and add an Inbound Rule:
   - Type: `PostgreSQL (5432)`
   - Source: Anywhere in VPC (`172.31.0.0/16`) or specifically your ECS security group.
3. Find your **Redis Security Group** and add an Inbound Rule:
   - Type: `Custom TCP (6379)`
   - Source: Anywhere in VPC.

---

## 4. 📦 Amazon ECR (Elastic Container Registry)

We need a place to store the Docker images built by GitHub Actions.

1. Navigate to **Amazon ECR**.
2. Click **Create repository**.
3. Visibility settings: **Private**.
4. Repository name: `pubmediq-backend`.
5. Click **Create repository**.

> Note the repository URI. You will need this for GitHub Actions.

---

## 5. 🚢 Amazon ECS (Fargate) & Load Balancer

### Step A: Task Definition
1. Navigate to **Amazon ECS** > **Task Definitions**.
2. Click **Create new task definition** (with Fargate).
3. Name: `pubmediq-api-task`.
4. Launch type: **AWS Fargate**.
5. OS: Linux/X86_64. Task memory: `1 GB`, Task CPU: `0.5 vCPU`.
6. Container details:
   - Name: `pubmediq-api`.
   - Image URI: `<YOUR_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/pubmediq-backend:latest`
   - Port mappings: `8000` (TCP).
7. Environment variables (Critical!):
   - Add all your `.env` variables here (e.g., `DATABASE_URL`, `REDIS_URL`, `PINECONE_API_KEY`, `OPENAI_API_KEY`, `LANGCHAIN_API_KEY`).
   - For `DATABASE_URL`, use the RDS endpoint (e.g., `postgresql+asyncpg://postgres:<password>@<rds-endpoint>:5432/pubmediq`).
   - For `REDIS_URL`, use the ElastiCache endpoint (e.g., `redis://<elasticache-endpoint>:6379/0`).
8. Click **Create**.

### Step B: Cluster & Service
1. Navigate to **Amazon ECS** > **Clusters**. Click **Create cluster**. Name it `pubmediq-cluster`.
2. Open the cluster, go to the **Services** tab, click **Create**.
3. Compute options: **Launch type -> Fargate**.
4. Task definition: Select `pubmediq-api-task`.
5. Service name: `pubmediq-service`.
6. Desired tasks: `1`.
7. **Networking**: Ensure you are in the default VPC and select subnets. Create a new security group (`pubmediq-ecs-sg`) allowing inbound port `8000` and `80`.
8. **Load Balancing**:
   - Choose **Application Load Balancer**.
   - Create a new ALB. Name: `pubmediq-alb`.
   - Target group: create new, Port `8000`.
9. Click **Create**.

---

## 6. 🔐 GitHub Actions Setup (OIDC)

To allow GitHub to push to your ECR safely without long-lived credentials:
1. Navigate to **IAM** > **Identity providers**. Add GitHub as an OpenID Connect provider.
2. Create an **IAM Role** (`github-actions-pubmediq-role`) and assign the **AmazonEC2ContainerRegistryPowerUser** policy.
3. Configure the Trust Policy to allow `repo:<YOUR_GITHUB_ORG>/<YOUR_REPO>:ref:refs/heads/main`.
4. In your GitHub Repository Settings > **Secrets and variables** > **Actions**, add:
   - `AWS_ROLE_ARN`: The ARN of the IAM role you just created.

---

## 🚀 Finalizing deployment

Once the infrastructure is up:
1. Push your code to the `main` branch.
2. GitHub Actions will build the Docker image, push it to ECR, and deploy the new version to ECS!
3. Upon startup, the `start.sh` entrypoint will run `alembic upgrade head` and start `uvicorn`, making your backend fully accessible via the Load Balancer DNS name.
