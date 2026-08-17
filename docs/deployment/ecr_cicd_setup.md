# PubMedIQ ECR CI/CD Setup

This deployment path builds a private image in GitHub Actions, pushes it to
Amazon ECR, and has the EC2 self-hosted runner pull that image. Docker Hub is
not used. It authenticates to AWS with GitHub OIDC and short-lived credentials,
not long-lived IAM user access keys.

## 1. Create the ECR repository

In AWS Console, open **Amazon ECR**, choose **Create repository**, and create
a private repository named `pubmediq-backend`. Enable scan on push. Keep image
tag mutability enabled because the workflow updates the `main` tag on each
deployment.

## 2. Configure GitHub OIDC in AWS IAM

Create an IAM identity provider with:

- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

Create an IAM role, for example `pubmediq-github-actions`, that trusts only
the `prod` branch of this repository. Replace the placeholders below with your
GitHub owner and repository name.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:<GITHUB_OWNER>/<GITHUB_REPOSITORY>:ref:refs/heads/prod"
        }
      }
    }
  ]
}
```

For repositories that use GitHub's newer ID-suffixed OIDC subject claim, use
the exact `sub` value shown by GitHub's OIDC claims documentation instead of
the value above.

Attach this ECR policy to the role, replacing the region, account ID, and
repository name:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ],
      "Resource": "arn:aws:ecr:<AWS_REGION>:<AWS_ACCOUNT_ID>:repository/pubmediq-backend"
    }
  ]
}
```

## 3. Configure GitHub Actions

Under **Settings > Secrets and variables > Actions**, add:

| Type | Name | Value |
| --- | --- | --- |
| Secret | `AWS_ROLE_ARN` | ARN of `pubmediq-github-actions` |
| Secret | `DB_PASSWORD` | Production Postgres password |
| Variable | `AWS_REGION` | ECR region, for example `ap-south-1` |
| Variable | `ECR_REPOSITORY` | `pubmediq-backend` |
| Variable | `DEPLOY_DIRECTORY` | EC2 directory holding `docker-compose.yml` and `.env` |

`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ACCOUNT_ID`,
`DOCKER_USERNAME`, and `DOCKER_PASSWORD` are not used by this workflow. Do not
add access keys to GitHub. After the OIDC workflow succeeds, deactivate and
delete any IAM user access key created only for CI/CD.

## 4. Prepare the EC2 deployment directory

Install Docker Engine and the Docker Compose plugin on EC2, then add the user
running the GitHub Actions runner to the `docker` group. The workflow runs
`docker compose`, so verify both `docker --version` and `docker compose version`
as that user. Register the machine as a repository self-hosted runner
in **Settings > Actions > Runners** and install the runner as a service.

Create the directory specified by `DEPLOY_DIRECTORY`, for example
`/home/runner/pubmediq`, and put the current `docker-compose.yml` there.
Create its `.env` from `.env.example` and set all application secrets,
including `PINECONE_API_KEY`, `OPENAI_API_KEY`, JWT secrets, and the database
password. The file stays only on EC2 and must not be committed.

Open only TCP port 8000 for the API (or preferably an Nginx/ALB proxy) and SSH
port 22 only from your administration IP. Do not expose PostgreSQL or Redis.

The `prod` branch triggers the workflow. It runs tests, builds ECR tags `main`
and `sha-<commit>`, then the self-hosted runner logs into ECR and recreates
only the API container. Confirm deployment with
`curl http://localhost:8000/api/v1/health` on EC2.
