# GitLab Deployment on Kubernetes

This directory contains the configuration for deploying GitLab on your Kubernetes cluster using built-in components for quick setup.

## Overview

The deployment integrates with your existing:
- ✅ **Traefik** ingress controller
- ✅ **cert-manager** (disabled TLS as requested)
- ✅ **Longhorn** storage
- ✅ **Domain**: `dungxbuif.com`

Uses built-in components:
- ✅ **PostgreSQL** (included in GitLab chart)
- ✅ **Redis** (included in GitLab chart)  
- ✅ **MinIO** (included in GitLab chart)

## URLs After Deployment

- **GitLab Web**: `http://gitlab.dungxbuif.com`
- **GitLab SSH**: `gitlab.dungxbuif.com:22`
- **Container Registry**: `http://registry-gitlab.dungxbuif.com`
- **MinIO UI**: `http://gitlab.dungxbuif.com/minio` (built-in)

## Files Structure

```
kubernetes-v1/gitlab/
├── gitlab-values.yaml                 # Main Helm values override
└── README.md                         # This file

Root directory:
└── deploy-gitlab.sh                   # Deployment script
```

## Prerequisites

1. **Helm 3 installed and GitLab repo added**:
   ```bash
   helm repo add gitlab https://charts.gitlab.io/
   helm repo update
   ```

2. **Sufficient cluster resources** (recommended minimum):
   - 8 vCPU
   - 30 GB RAM
   - Longhorn storage available

## Deployment Steps

### Simple One-Step Deployment
```bash
./deploy-gitlab.sh
```

## Manual Deployment (Alternative)

If you prefer manual deployment:

1. **Create namespace**:
   ```bash
   kubectl create namespace gitlab-system
   ```

2. **Deploy GitLab**:
   ```bash
   helm upgrade --install gitlab gitlab/gitlab \
       --namespace gitlab-system \
       --values kubernetes-v1/gitlab/gitlab-values.yaml \
       --timeout 15m
   ```

## Configuration Details

### Key Features Enabled:
- ✅ **Built-in PostgreSQL**: Database included in GitLab chart
- ✅ **Built-in Redis**: Cache and job queue included in GitLab chart  
- ✅ **Built-in MinIO**: Object storage included in GitLab chart
- ✅ **Traefik Integration**: Native Traefik ingress support
- ✅ **Longhorn Storage**: All persistent volumes use Longhorn
- ✅ **No TLS**: HTTP-only as requested
- ✅ **SSH Support**: Git over SSH on port 22
- ✅ **Container Registry**: Full Docker registry support

### Key Features Disabled:
- ❌ **Internal cert-manager**: Uses your existing cert-manager
- ❌ **Internal nginx**: Uses your Traefik instead
- ❌ **TLS**: Disabled as requested
- ❌ **GitLab Runner**: Disabled (can be enabled later)

### Storage Configuration:
- **PostgreSQL**: 8Gi Longhorn volume
- **Redis**: 8Gi Longhorn volume
- **MinIO**: 10Gi Longhorn volume  
- **Gitaly**: 50Gi Longhorn volume (Git repositories)

### Built-in Components:
All storage is handled by the included components:
- **PostgreSQL** for database
- **Redis** for caching and job queues
- **MinIO** for object storage (artifacts, uploads, registry, etc.)
- **Gitaly** for Git repository storage

## Post-Deployment

### 1. Get Root Password
```bash
kubectl get secret gitlab-gitlab-initial-root-password -n gitlab-system -o jsonpath='{.data.password}' | base64 --decode
```

### 2. Update DNS
Point these domains to your Traefik external IP:
- `gitlab.dungxbuif.com`
- `registry-gitlab.dungxbuif.com`

### 3. Access GitLab
- Navigate to `http://gitlab.dungxbuif.com`
- Login with `root` and the password from step 1
- Complete the setup wizard

## Monitoring & Troubleshooting

### Check Deployment Status
```bash
# Overall status
kubectl get pods -n gitlab-system

# Ingress status
kubectl get ingress -n gitlab-system

# MinIO status
kubectl get pods -n minio-system

# GitLab logs
kubectl logs -n gitlab-system -l app=webservice
```

### Common Issues

1. **GitLab pods pending**: Check Longhorn storage availability
2. **MinIO connection failed**: Verify MinIO is running and accessible
3. **Ingress not working**: Check Traefik ingress controller status
4. **Buckets not found**: Run the bucket setup script

### Resource Usage
The deployment is configured for moderate resource usage:
- **GitLab Web**: 300m CPU, 1.5Gi RAM
- **Sidekiq**: 100m CPU, 625Mi RAM  
- **Gitaly**: 100m CPU, 200Mi RAM
- **PostgreSQL**: Standard Bitnami resources
- **Redis**: Standard Bitnami resources

## Scaling

To scale GitLab components:

1. **Edit values**:
   ```yaml
   gitlab:
     webservice:
       minReplicas: 2
       maxReplicas: 4
   ```

2. **Upgrade deployment**:
   ```bash
   helm upgrade gitlab gitlab/gitlab \
       --namespace gitlab-system \
       --values kubernetes-v1/gitlab/gitlab-values.yaml
   ```

## Backup & Restore

GitLab is configured to store backups in the `gitlab-backups` MinIO bucket.

### Create Backup
```bash
kubectl exec -n gitlab-system -it $(kubectl get pods -n gitlab-system -l app=toolbox -o jsonpath='{.items[0].metadata.name}') -- backup-utility
```

### List Backups
```bash
mc ls gitlab-minio/gitlab-backups/
```

## Integration with Existing Services

### ArgoCD Integration
- Use GitLab as your Git repository source
- Configure ArgoCD to pull from GitLab repos
- Complete GitOps workflow within your cluster

### Authentik Integration (Optional)
Can be configured post-deployment for SSO:
```yaml
global:
  appConfig:
    omniauth:
      enabled: true
      providers:
        - secret: gitlab-authentik-oidc
```

## Support

For issues:
1. Check the troubleshooting section above
2. Review GitLab Helm chart documentation: https://docs.gitlab.com/charts/
3. Check Kubernetes events: `kubectl get events -n gitlab-system`
