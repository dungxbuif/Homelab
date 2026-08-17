#!/bin/bash

# Ktunnel GitLab Deployment Script
# This script deploys all necessary components for ktunnel GitLab setup

set -e

echo "🚀 Deploying Ktunnel GitLab Setup..."
echo "=================================="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster"
    exit 1
fi

echo "✅ Kubernetes cluster connection verified"

# Deploy components in order
echo ""
echo "📦 Step 1: Creating namespace..."
kubectl apply -f namespace.yml

echo "🔐 Step 2: Setting up RBAC permissions..."
kubectl apply -f rbac.yml

echo "🖥️  Step 3: Deploying ktunnel server..."
kubectl apply -f ktunnel-server-deployment.yml

echo "🔗 Step 4: Creating GitLab services and endpoints..."
kubectl apply -f gitlab-services.yml

echo "🌐 Step 5: Setting up ingress routes..."
kubectl apply -f gitlab-ingress.yml

# Wait for deployment to be ready
echo ""
echo "⏳ Waiting for ktunnel server to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/ktunnel-server -n ktunnel

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Deployment Status:"
echo "===================="
kubectl get pods -n ktunnel
echo ""
kubectl get services -n ktunnel
echo ""
kubectl get ingressroutes -n ktunnel
echo ""

echo "📝 Next Steps:"
echo "=============="
echo "1. Ensure your local GitLab is running on ports 80 and 5000"
echo "2. Install ktunnel binary locally: ./install-ktunnel.sh"
echo "3. Create tunnels: ./create-tunnels.sh"
echo "4. Access GitLab at: https://gitlab.dungxbuif.com"
echo ""
echo "🔍 To check logs: kubectl logs -n ktunnel deployment/ktunnel-server"
echo "🔧 To troubleshoot: kubectl describe pods -n ktunnel"
