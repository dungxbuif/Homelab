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
