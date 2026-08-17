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
