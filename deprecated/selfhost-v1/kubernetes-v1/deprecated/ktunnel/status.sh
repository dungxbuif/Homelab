#!/bin/bash

# Ktunnel Status Check Script
# Displays the current status of ktunnel deployment and tunnels

echo "📊 Ktunnel GitLab Status"
echo "======================="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace ktunnel &> /dev/null; then
    echo "❌ ktunnel namespace doesn't exist"
    echo "   Run: ./deploy.sh"
    exit 1
fi

echo "✅ ktunnel namespace exists"

# Check Kubernetes deployment status
echo ""
echo "🏗️  Kubernetes Deployment Status:"
echo "=================================="

echo "📦 Pods:"
kubectl get pods -n ktunnel -o wide || echo "   No pods found"

echo ""
echo "🔗 Services:"
kubectl get services -n ktunnel || echo "   No services found"

echo ""
echo "📍 Endpoints:"
kubectl get endpoints -n ktunnel || echo "   No endpoints found"

echo ""
echo "🌐 Ingress Routes:"
kubectl get ingressroutes -n ktunnel 2>/dev/null || echo "   No HTTP ingress routes found"
kubectl get ingressroutetcp -n ktunnel 2>/dev/null || echo "   No TCP ingress routes found"

# Check ktunnel server logs (last 10 lines)
echo ""
echo "📋 Ktunnel Server Logs (last 10 lines):"
echo "========================================"
kubectl logs -n ktunnel deployment/ktunnel-server --tail=10 2>/dev/null || echo "   Unable to fetch logs"

# Check local tunnel status
echo ""
echo "🔗 Local Tunnel Status:"
echo "======================="

if command -v ktunnel &> /dev/null; then
    TUNNEL_PIDS=$(pgrep -f "ktunnel expose" 2>/dev/null || true)
    
    if [ -z "$TUNNEL_PIDS" ]; then
        echo "❌ No active tunnels found"
        echo "   Run: ./create-tunnels.sh"
    else
        echo "✅ Active tunnels:"
        echo "$TUNNEL_PIDS" | while read pid; do
            ps -p $pid -o pid,cmd --no-headers | sed 's/^/   /'
        done
    fi
    
    echo ""
    echo "📋 Ktunnel remote status:"
    ktunnel list -n ktunnel 2>/dev/null || echo "   Unable to list remote tunnels"
else
    echo "❌ ktunnel binary not found"
    echo "   Run: ./install-ktunnel.sh"
fi

# Test connectivity
echo ""
echo "🔍 Connectivity Tests:"
echo "====================="

test_url() {
    local url=$1
    local name=$2
    
    echo -n "   Testing $name ($url): "
    if curl -s -k --connect-timeout 5 --max-time 10 "$url" > /dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ FAILED"
    fi
}

test_url "https://gitlab.dungxbuif.com" "GitLab Web"
test_url "https://registry.gitlab.dungxbuif.com/v2/" "GitLab Registry"
test_url "https://ktunnel.dungxbuif.com" "Ktunnel Management"

echo ""
echo "📖 Quick Actions:"
echo "=================="
echo "Restart tunnels:   ./stop-tunnels.sh && ./create-tunnels.sh"
echo "View server logs:  kubectl logs -n ktunnel deployment/ktunnel-server -f"
echo "Debug endpoints:   kubectl describe endpoints -n ktunnel"
echo "Check local GitLab: docker ps | grep gitlab"
