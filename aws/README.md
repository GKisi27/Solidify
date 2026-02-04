# AWS Configuration

## 📁 Structure

```
aws/
├── buildspec.yml           # CodeBuild specification
├── appspec.yml             # CodeDeploy specification
└── cloudformation/
    ├── ecs-cluster.yml     # ECS cluster template
    ├── redis.yml           # ElastiCache Redis
    └── s3-bucket.yml       # S3 storage bucket
```

## 🚀 Deployment Pipeline

```
GitHub Push
     │
     ▼
┌─────────────┐
│ CodePipeline │
└──────┬──────┘
       ▼
┌─────────────┐
│  CodeBuild  │──▶ Build Docker images
└──────┬──────┘
       ▼
┌─────────────┐
│  CodeDeploy │──▶ Deploy to ECS
└──────┬──────┘
       ▼
   ECS Cluster
```

## ⚙️ CloudFormation

Deploy infrastructure:

```bash
# Create S3 bucket
aws cloudformation deploy \
  --template-file cloudformation/s3-bucket.yml \
  --stack-name solidify-storage

# Create Redis cluster
aws cloudformation deploy \
  --template-file cloudformation/redis.yml \
  --stack-name solidify-redis

# Create ECS cluster
aws cloudformation deploy \
  --template-file cloudformation/ecs-cluster.yml \
  --stack-name solidify-ecs
```
