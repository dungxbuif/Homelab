#!/bin/bash

# Ktunnel Tunnel Creation Script
# Creates tunnels from local GitLab to Kubernetes cluster

set -e

NAMESPACE="ktunnel"
GITLAB_WEB_PORT="80"
GITLAB_REGISTRY_PORT="5000"
GITLAB_SSH_PORT="22"

echo "🔗 Creating ktunnel tunnels for GitLab..."
echo "========================================"

# Check if ktunnel is installed
if ! command -v ktunnel &> /dev/null; then
    echo "❌ ktunnel is not installed"
    echo "   Run: ./install-ktunnel.sh"
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if ktunnel server is running
echo "🔍 Checking if ktunnel server is running..."
if ! kubectl get deployment ktunnel-server -n $NAMESPACE &> /dev/null; then
    echo "❌ ktunnel server is not deployed"
    echo "   Run: ./deploy.sh"
    exit 1
fi

# Wait for ktunnel server to be ready
kubectl wait --for=condition=available --timeout=60s deployment/ktunnel-server -n $NAMESPACE

echo "✅ ktunnel server is ready"

# Function to check if local port is in use
check_local_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "✅ Local $service service detected on port $port"
        return 0
    else
        echo "⚠️  Warning: No service detected on local port $port for $service"
        return 1
    fi
}

# Check local GitLab services
echo ""
echo "🔍 Checking local GitLab services..."
WEB_AVAILABLE=$(check_local_port $GITLAB_WEB_PORT "GitLab Web" && echo "true" || echo "false")
REGISTRY_AVAILABLE=$(check_local_port $GITLAB_REGISTRY_PORT "GitLab Registry" && echo "true" || echo "false")
SSH_AVAILABLE=$(check_local_port $GITLAB_SSH_PORT "GitLab SSH" && echo "true" || echo "false")

if [[ "$WEB_AVAILABLE" == "false" ]]; then
    echo "❌ GitLab web service is not running on port $GITLAB_WEB_PORT"
    echo "   Make sure your GitLab Docker container is running and exposing port $GITLAB_WEB_PORT"
    exit 1
fi

# Function to create tunnel
create_tunnel() {
    local service_name=$1
    local local_port=$2
    local remote_port=$3
    local description=$4
    
    echo ""
    echo "🔗 Creating tunnel for $description..."
    echo "   Service: $service_name"
    echo "   Mapping: localhost:$local_port -> cluster:$remote_port"
    
    # Kill existing tunnel if it exists
    pkill -f "ktunnel expose $service_name" 2>/dev/null || true
    
    # Create tunnel in background
    nohup ktunnel expose $service_name $local_port:$remote_port -n $NAMESPACE > /tmp/ktunnel-$service_name.log 2>&1 &
    
    # Wait a moment for tunnel to establish
    sleep 2
    
    # Check if tunnel is running
    if pgrep -f "ktunnel expose $service_name" > /dev/null; then
        echo "✅ Tunnel created successfully"
    else
        echo "❌ Failed to create tunnel"
        echo "   Check logs: cat /tmp/ktunnel-$service_name.log"
        return 1
    fi
}

# Create tunnels
echo ""
echo "🚀 Creating tunnels..."
echo "===================="

# GitLab Web tunnel (mandatory)
create_tunnel "gitlab-web" $GITLAB_WEB_PORT $GITLAB_WEB_PORT "GitLab Web Interface"

# GitLab Registry tunnel (if available)
if [[ "$REGISTRY_AVAILABLE" == "true" ]]; then
    create_tunnel "gitlab-registry" $GITLAB_REGISTRY_PORT $GITLAB_REGISTRY_PORT "GitLab Container Registry"
else
    echo "⏭️  Skipping GitLab Registry tunnel (service not detected)"
fi

# GitLab SSH tunnel (optional)
if [[ "$SSH_AVAILABLE" == "true" ]]; then
    read -p "Do you want to create SSH tunnel for Git operations? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_tunnel "gitlab-ssh" $GITLAB_SSH_PORT $GITLAB_SSH_PORT "GitLab SSH"
    fi
else
    echo "⏭️  Skipping GitLab SSH tunnel (service not detected)"
fi

# Wait for tunnels to stabilize
echo ""
echo "⏳ Waiting for tunnels to stabilize..."
sleep 5

# Verify tunnels
echo ""
echo "🔍 Verifying tunnel status..."
echo "============================"
kubectl get endpoints -n $NAMESPACE

echo ""
echo "📋 Active tunnel processes:"
pgrep -f "ktunnel expose" | while read pid; do
    ps -p $pid -o pid,cmd --no-headers
done

echo ""
echo "🎉 Tunnel creation completed!"
echo ""
echo "📖 Access URLs:"
echo "==============="
echo "GitLab Web:       https://gitlab.dungxbuif.com"
if [[ "$REGISTRY_AVAILABLE" == "true" ]]; then
    echo "GitLab Registry:  https://registry.gitlab.dungxbuif.com"
fi
echo "Ktunnel Mgmt:     https://ktunnel.dungxbuif.com"
echo ""
echo "📝 Tunnel Management:"
echo "===================="
echo "List tunnels:     ktunnel list -n $NAMESPACE"
echo "Stop all tunnels: ./stop-tunnels.sh"
echo "View logs:        ls /tmp/ktunnel-*.log"
echo ""
echo "🔧 Troubleshooting:"
echo "=================="
echo "Check endpoints:  kubectl get endpoints -n $NAMESPACE"
echo "Check server:     kubectl logs -n $NAMESPACE deployment/ktunnel-server"
