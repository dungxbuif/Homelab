---
type: infrastructure-runbook
title: 'LocalStack on Kubernetes'
description: 'Internal-only LocalStack deployment for AWS SAA lab practice on the homelab Kubernetes cluster'
timestamp: 2026-07-09T00:00:00Z
tags: [homelab, kubernetes, localstack, aws, lab]
---

# LocalStack on Kubernetes

Internal LocalStack deployment for AWS SAA lab practice.

## Design

- Namespace: `localstack`
- Exposure: `ClusterIP` only
- LAN domain endpoint: `https://localstack.dungxbuif.com`
- Local access: `kubectl port-forward`
- Cluster endpoint: `http://localstack.localstack.svc.cluster.local:4566`
- Local endpoint after port-forward: `http://localhost:4566`
- Storage: Longhorn PVC `localstack-data`, 8Gi, `ReadWriteOnce`
- Image: `localstack/localstack:3.8.1`
- Public internet export: disabled
- Docker-in-Docker / privileged mode: disabled

This keeps LocalStack aligned with the homelab portless constraint. The domain endpoint is intended for LAN/split-horizon access through Caddy, not public VPS export.

The latest/stable LocalStack image can require `LOCALSTACK_AUTH_TOKEN`. This lab pins an older community image so AWS SAA practice can run without storing a LocalStack credential in the vault. To use the latest image later, create a Kubernetes Secret for `LOCALSTACK_AUTH_TOKEN` and update the deployment image tag deliberately.

## Supported Lab Scope

Good fit:

- S3
- SQS
- SNS
- DynamoDB
- EventBridge
- API Gateway basics
- SSM basics

Limited fit:

- Lambda container/runtime behavior, unless Docker-in-Docker is enabled deliberately.
- VPC, EC2, RDS, ALB, CloudFront, Route 53 behavior. Use AWS Educate/AWS real labs or architecture diagrams for those.

## Apply

```bash
cd homelab/iac/k8s/localstack
./apply.sh
```

## Status

```bash
cd homelab/iac/k8s/localstack
./status.sh
```

## Local Access

Preferred LAN endpoint:

```bash
source ./env.local.sh
curl "$LOCALSTACK_ENDPOINT/_localstack/health"
aws --endpoint-url="$LOCALSTACK_ENDPOINT" s3 ls
```

Port-forward fallback:

```bash
cd homelab/iac/k8s/localstack
./port-forward.sh
```

Then use:

```bash
curl http://localhost:4566/_localstack/health
aws --endpoint-url=http://localhost:4566 s3 ls
```

For local shell labs with the domain endpoint:

```bash
cd homelab/iac/k8s/localstack
source ./env.local.sh
aws --endpoint-url="$LOCALSTACK_ENDPOINT" s3 ls
```

For workloads running inside the Kubernetes cluster:

```bash
source ./env.cluster.sh
aws --endpoint-url="$LOCALSTACK_ENDPOINT" s3 ls
```

Use dummy credentials for all LocalStack labs:

```text
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
```

## Endpoint Rule

Keep LocalStack private to the lab while still giving it a stable LAN endpoint:

- Do use `https://localstack.dungxbuif.com` from LAN clients.
- Do use `http://localstack.localstack.svc.cluster.local:4566` from workloads inside K8s.
- Do keep Caddy routing LAN/split-horizon only unless there is a separate public export decision.
- Do not add NodePort or direct service LoadBalancer for LocalStack.

Pi Caddy route applied in `/ssd-data/infra/Caddyfile`:

```caddy
@localstack {
    host localstack.dungxbuif.com
    remote_ip 10.10.0.0/24 172.16.0.0/12 10.66.66.0/24 10.0.0.0/24
}
handle @localstack {
    reverse_proxy 10.10.0.30:80
}
@localstack_external host localstack.dungxbuif.com
handle @localstack_external {
    respond "Access Denied - Internal Only" 403
}
```

Caddy backup from this change: `/ssd-data/infra/Caddyfile.bak-20260709-localstack`.

## Smoke Test

```bash
cd homelab/iac/k8s/localstack
./smoke-test.sh
```

## Removal

```bash
kubectl delete -k homelab/iac/k8s/localstack
```

That removes the PVC as declared by the manifest. If you need to preserve lab data, back it up first or delete only the deployment/service.
