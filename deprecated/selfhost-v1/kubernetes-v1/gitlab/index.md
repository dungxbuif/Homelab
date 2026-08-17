---
type: Reference
title: "Code Index: gitlab"
description: "Aggregated code index for gitlab folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: gitlab

> This index aggregates code files in the [[gitlab/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [deploy-gitlab.sh](./deploy-gitlab.sh)

```bash
#!/bin/bash

# GitLab Deployment Script for dungxbuif.com
# This script deploys GitLab with your existing MinIO and Traefik infrastructure

set -e

echo "🚀 Deploying GitLab on Kubernetes with external MinIO..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if we're in the right directory
if [ ! -d "kubernetes-v1/gitlab" ]; then
    echo "Please run this script from the selfhost directory"
    exit 1
fi

print_success "Using built-in PostgreSQL, Redis, and MinIO components"

# Create GitLab namespace
print_status "Creating GitLab namespace..."
kubectl create namespace gitlab --dry-run=client -o yaml | kubectl apply -f -

print_success "GitLab namespace ready"

# Apply GitLab secrets
print_status "Applying GitLab secrets..."
kubectl apply -f kubernetes-v1/gitlab/gitlab-secrets.yaml -n gitlab

# Add GitLab Helm repository
print_status "Adding GitLab Helm repository..."
helm repo add gitlab https://charts.gitlab.io/
helm repo update

# Deploy GitLab
print_status "Deploying GitLab with custom values..."
helm upgrade --install gitlab gitlab/gitlab \
    --namespace gitlab \
    --values kubernetes-v1/gitlab/gitlab-values.yaml \
    --timeout 15m

print_success "GitLab deployment initiated!"

print_status "Waiting for GitLab to be ready..."
kubectl wait --for=condition=ready pod -l app=webservice --namespace=gitlab --timeout=600s

print_success "GitLab deployment completed!"

echo ""
echo "🎉 GitLab is now deployed with built-in components!"
echo ""
echo "📊 Access URLs:"
echo "  🌐 GitLab Web:     https://gitlab.dungxbuif.com"
echo "  📦 Registry:       https://registry-gitlab.dungxbuif.com"
echo ""
echo "🔑 To get the root password:"
echo "  kubectl get secret gitlab-gitlab-initial-root-password -n gitlab -o jsonpath='{.data.password}' | base64 --decode"
echo ""
echo "📝 Next steps:"
echo "  1. Update your DNS to point domains to Traefik IP"
echo "  2. Access GitLab and complete setup"
echo "  3. Configure additional settings as needed"
echo ""
echo "🔧 To check deployment status:"
echo "  kubectl get pods -n gitlab"
echo "  kubectl get ingress -n gitlab"

```

---

## [gitlab-secrets.yaml](./gitlab-secrets.yaml)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gitlab-object-storage
  namespace: gitlab
type: Opaque
stringData:
  connection: |
    provider: AWS
    region: us-east-1
    aws_access_key_id: admin
    aws_secret_access_key: "<MINIO_PASSWORD>"
    host: minio-service.minio-system.svc.cluster.local
    endpoint: http://minio-service.minio-system.svc.cluster.local:80
    path_style: true
    aws_signature_version: 4
    use_ssl: false

---
apiVersion: v1
kind: Secret
metadata:
  name: gitlab-registry-storage
  namespace: gitlab
type: Opaque
stringData:
  config: |
    s3:
      region: us-east-1
      bucket: gitlab-registry
      accesskey: admin
      secretkey: "<MINIO_PASSWORD>"
      regionendpoint: http://minio-service.minio-system.svc.cluster.local:80
      pathstyle: true
      v4auth: true
      secure: false

---
apiVersion: v1
kind: Secret
metadata:
  name: gitlab-minio-secret
  namespace: gitlab
type: Opaque
stringData:
  accesskey: admin
  secretkey: "<MINIO_PASSWORD>"

---
apiVersion: v1
kind: Secret
metadata:
  name: gitlab-initial-root-password
  namespace: gitlab
type: Opaque
stringData:
  password: "<GITLAB_ADMIN_PASSWORD>"

```

---

## [gitlab-values.yaml](./gitlab-values.yaml)

```yaml
global:
  hosts:
    domain: dungxbuif.com
    gitlab:
      name: gitlab.dungxbuif.com
    registry:
      name: registry-gitlab.dungxbuif.com
    ssh: gitlab.dungxbuif.com 
  ingress:
    enabled: true
    provider: traefik
    class: traefik
    configureCertmanager: false 
    tls:
      enabled: false 

  minio:
    enabled: false

  appConfig:
    object_store:
      enabled: true
      proxy_download: true
      storage_options: {}
      connection:
        secret: gitlab-object-storage
        key: connection

    artifacts:
      enabled: true
      bucket: gitlab-artifacts

    lfs:
      enabled: true
      bucket: gitlab-lfs

    uploads:
      enabled: true
      bucket: gitlab-uploads

    packages:
      enabled: true
      bucket: gitlab-packages

    externalDiffs:
      enabled: false
      bucket: gitlab-diffs

    terraformState:
      enabled: true
      bucket: gitlab-terraform-state

    dependencyProxy:
      enabled: true
      bucket: gitlab-dependency-proxy

    backups:
      bucket: gitlab-backups
      tmpBucket: gitlab-tmp
      objectStorage:
        config:
          secret: gitlab-object-storage
          key: connection

  shell:
    port: 22
    ingress:
      enabled: false  
ingress:
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: "websecure" 
installCertmanager: false

nginx-ingress:
  enabled: false

registry:
  enabled: true
  storage:
    secret: gitlab-registry-storage
    key: config
  ingress:
    tls:
      enabled: false 
gitlab-runner:
  install: false 

postgresql:
  install: true
  primary:
    persistence:
      storageClass: longhorn
      size: 512Mi 

redis:
  install: true
  master:
    persistence:
      storageClass: longhorn
      size: 512Mi

gitlab-shell:
  enabled: true
  service:
    type: ClusterIP  # Don't expose SSH externally through ingress
  ingress:
    enabled: false  # Disable ingress for SSH service

  toolbox:
    backups:
      objectStorage:
        config:
          secret: gitlab-object-storage
          key: connection

gitlab:
  webservice:
    minReplicas: 1
    maxReplicas: 2
    resources:
      requests:
        cpu: 300m
        memory: 1.5Gi
      limits:
        cpu: 1
        memory: 2Gi

  sidekiq:
    minReplicas: 1
    maxReplicas: 2
    resources:
      requests:
        cpu: 100m
        memory: 625Mi
      limits:
        cpu: 500m
        memory: 1Gi

  gitaly:
    persistence:
      storageClass: longhorn
      size: 512Mi
    resources:
      requests:
        cpu: 100m
        memory: 200Mi
      limits:
        cpu: 500m
        memory: 1Gi

# Monitoring (optional)
prometheus:
  install: false

grafana:
  enabled: false

```

---

## [setup-minio-buckets.sh](./setup-minio-buckets.sh)

```bash
#!/bin/bash

# MinIO Bucket Setup Script for GitLab
# This script creates all required buckets in your MinIO instance

set -e

echo "🪣 Setting up MinIO buckets for GitLab..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# MinIO connection details
MINIO_ENDPOINT="https://storage.dungxbuif.com"
MINIO_ACCESS_KEY="admin"
MINIO_SECRET_KEY="<MINIO_PASSWORD>"

# List of required buckets
BUCKETS=(
    "gitlab-artifacts"
    "gitlab-lfs"
    "gitlab-uploads"
    "gitlab-packages"
    "gitlab-diffs"
    "gitlab-terraform-state"
    "gitlab-dependency-proxy"
    "gitlab-registry"
    "gitlab-backups"
    "gitlab-tmp"
)

# Check if mc (MinIO client) is installed
if ! command -v mc &> /dev/null; then
    print_error "MinIO client (mc) is not installed."
    echo "Please install it first:"
    echo "  # For Linux:"
    echo "  curl https://dl.min.io/client/mc/release/linux-amd64/mc -o mc"
    echo "  chmod +x mc"
    echo "  sudo mv mc /usr/local/bin/"
    echo ""
    echo "  # For macOS:"
    echo "  brew install minio/stable/mc"
    echo ""
    echo "  # For other platforms, see: https://min.io/docs/minio/linux/reference/minio-mc.html"
    exit 1
fi

# Configure MinIO client
print_status "Configuring MinIO client..."
mc alias set gitlab-minio $MINIO_ENDPOINT $MINIO_ACCESS_KEY $MINIO_SECRET_KEY

# Test connection
print_status "Testing MinIO connection..."
if ! mc admin info gitlab-minio &> /dev/null; then
    print_error "Failed to connect to MinIO at $MINIO_ENDPOINT"
    echo "Please check:"
    echo "  1. MinIO is running: kubectl get pods -n minio-system"
    echo "  2. MinIO service is accessible: kubectl get svc -n minio-system"
    echo "  3. DNS/ingress is configured correctly"
    exit 1
fi

print_success "Connected to MinIO successfully"

# Create buckets
print_status "Creating GitLab buckets..."
for bucket in "${BUCKETS[@]}"; do
    if mc ls gitlab-minio/$bucket &> /dev/null; then
        print_status "Bucket '$bucket' already exists"
    else
        print_status "Creating bucket '$bucket'..."
        mc mb gitlab-minio/$bucket
        print_success "Created bucket '$bucket'"
    fi
done

# Set bucket policies (public read for registry if needed)
print_status "Setting bucket policies..."
mc anonymous set public gitlab-minio/gitlab-registry 2>/dev/null || true

print_success "All MinIO buckets are ready for GitLab!"

echo ""
echo "📊 Created buckets:"
for bucket in "${BUCKETS[@]}"; do
    echo "  ✅ $bucket"
done

echo ""
echo "🔗 MinIO endpoints:"
echo "  🌐 Web UI:     http://minio.dungxbuif.com"
echo "  📡 API:        http://storage.dungxbuif.com"
echo ""
echo "🔑 Credentials:"
echo "  👤 Access Key: $MINIO_ACCESS_KEY"
echo "  🔐 Secret Key: $MINIO_SECRET_KEY"
echo ""
echo "✅ You can now deploy GitLab with: ./deploy-gitlab.sh"

```

---
