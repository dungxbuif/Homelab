#!/bin/bash

# Ktunnel GitLab Cleanup Script
# Removes all ktunnel GitLab components from Kubernetes

set -e

echo "🧹 Cleaning up Ktunnel GitLab Setup..."
echo "====================================="

# Stop local tunnels first
if [ -f "./stop-tunnels.sh" ]; then
    echo "🛑 Stopping local tunnels..."
    ./stop-tunnels.sh
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace ktunnel &> /dev/null; then
    echo "ℹ️  ktunnel namespace doesn't exist, nothing to clean up"
    exit 0
fi

echo ""
echo "🗑️  Removing Kubernetes resources..."

# Remove ingress routes first
echo "   Removing ingress routes..."
kubectl delete ingressroutes --all -n ktunnel 2>/dev/null || true
kubectl delete ingressroutetcp --all -n ktunnel 2>/dev/null || true

# Remove services and endpoints
echo "   Removing services and endpoints..."
kubectl delete services --all -n ktunnel 2>/dev/null || true
kubectl delete endpoints --all -n ktunnel 2>/dev/null || true

# Remove deployments
echo "   Removing deployments..."
kubectl delete deployment ktunnel-server -n ktunnel 2>/dev/null || true

# Remove RBAC
echo "   Removing RBAC resources..."
kubectl delete rolebinding ktunnel-server -n ktunnel 2>/dev/null || true
kubectl delete role ktunnel-server -n ktunnel 2>/dev/null || true
kubectl delete serviceaccount ktunnel-server -n ktunnel 2>/dev/null || true

# Remove namespace (this will clean up any remaining resources)
echo "   Removing namespace..."
kubectl delete namespace ktunnel

echo ""
echo "✅ Cleanup completed successfully!"
echo ""
echo "📝 To redeploy:"
echo "==============="
echo "./deploy.sh"
