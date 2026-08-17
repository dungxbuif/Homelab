---
type: Reference
title: "Code Index: ktunnel"
description: "Aggregated code index for ktunnel folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: ktunnel

> This index aggregates code files in the [[ktunnel/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [cleanup.sh](./cleanup.sh)

```bash
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

```

---

## [create-tunnels.sh](./create-tunnels.sh)

```bash
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

```

---

## [deploy.sh](./deploy.sh)

```bash
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

```

---

## [gitlab-ingress.yml](./gitlab-ingress.yml)

```yaml
# GitLab Web Ingress
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: gitlab-web-ingress
  namespace: ktunnel
  labels:
    app: gitlab-tunnel
    component: web-ingress
    tunnel-type: gitlab
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`gitlab.dungxbuif.com`)
      kind: Rule
      services:
        - name: gitlab-web
          port: 80
  tls: {}
---
# GitLab Registry Ingress
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: gitlab-registry-ingress
  namespace: ktunnel
  labels:
    app: gitlab-tunnel
    component: registry-ingress
    tunnel-type: gitlab
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`registry.gitlab.dungxbuif.com`)
      kind: Rule
      services:
        - name: gitlab-registry
          port: 5000
  tls: {}
---
# GitLab SSH Ingress (TCP)
apiVersion: traefik.io/v1alpha1
kind: IngressRouteTCP
metadata:
  name: gitlab-ssh-ingress
  namespace: ktunnel
  labels:
    app: gitlab-tunnel
    component: ssh-ingress
    tunnel-type: gitlab
spec:
  entryPoints:
    - ssh
  routes:
    - match: HostSNI(`*`)
      services:
        - name: gitlab-ssh
          port: 22
---
# Ktunnel Server Management Interface
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: ktunnel-server-ingress
  namespace: ktunnel
  labels:
    app: ktunnel-server
    component: management-ingress
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`ktunnel.dungxbuif.com`)
      kind: Rule
      services:
        - name: ktunnel-server-service
          port: 8000
  tls: {}

```

---

## [gitlab-services.yml](./gitlab-services.yml)

```yaml
# GitLab Web Service
apiVersion: v1
kind: Service
metadata:
  name: gitlab-web
  namespace: ktunnel
  labels:
    app: gitlab-tunnel
    component: web
    tunnel-type: gitlab
spec:
  ports:
    - port: 80
      targetPort: 80
      protocol: TCP
      name: http
  type: ClusterIP
# GitLab Web Endpoints will be managed by ktunnel dynamically
---
# GitLab Registry Service
apiVersion: v1
kind: Service
metadata:
  name: gitlab-registry
  namespace: ktunnel
  labels:
    app: gitlab-tunnel
    component: registry
    tunnel-type: gitlab
spec:
  ports:
    - port: 5000
      targetPort: 5000
      protocol: TCP
      name: registry
  type: ClusterIP
# GitLab Registry Endpoints will be managed by ktunnel dynamically
---
# GitLab SSH Service (Optional)
apiVersion: v1
kind: Service
metadata:
  name: gitlab-ssh
  namespace: ktunnel
  labels:
    app: gitlab-tunnel
    component: ssh
    tunnel-type: gitlab
spec:
  ports:
    - port: 22
      targetPort: 22
      protocol: TCP
      name: ssh
  type: ClusterIP
# GitLab SSH Endpoints will be managed by ktunnel dynamically

```

---

## [install-ktunnel.sh](./install-ktunnel.sh)

```bash
#!/bin/bash

# Ktunnel Binary Installation Script
# Downloads and installs ktunnel binary locally

set -e

KTUNNEL_VERSION="v1.6.1"
KTUNNEL_ARCH="Linux_x86_64"
KTUNNEL_URL="https://github.com/omrikiei/ktunnel/releases/download/${KTUNNEL_VERSION}/ktunnel_${KTUNNEL_VERSION#v}_${KTUNNEL_ARCH}.tar.gz"

echo "📥 Installing ktunnel ${KTUNNEL_VERSION}..."
echo "========================================"

# Check if ktunnel is already installed
if command -v ktunnel &> /dev/null; then
    CURRENT_VERSION=$(ktunnel version 2>/dev/null | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
    echo "ℹ️  ktunnel is already installed (version: ${CURRENT_VERSION})"
    read -p "Do you want to reinstall? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ Keeping existing installation"
        exit 0
    fi
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo "📦 Downloading ktunnel ${KTUNNEL_VERSION}..."
wget -q --show-progress "$KTUNNEL_URL" -O ktunnel.tar.gz

echo "📁 Extracting archive..."
tar -xzf ktunnel.tar.gz

echo "🔧 Installing to /usr/local/bin..."
sudo mv ktunnel /usr/local/bin/
sudo chmod +x /usr/local/bin/ktunnel

# Verify installation
echo "✅ Verifying installation..."
if command -v ktunnel &> /dev/null; then
    INSTALLED_VERSION=$(ktunnel version 2>/dev/null | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
    echo "🎉 ktunnel ${INSTALLED_VERSION} installed successfully!"
else
    echo "❌ Installation failed"
    exit 1
fi

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo ""
echo "📝 Usage:"
echo "========="
echo "ktunnel expose <service-name> <local-port>:<remote-port> -n <namespace>"
echo ""
echo "📖 For more information: ktunnel --help"

```

---

## [ktunnel-server-deployment.yml](./ktunnel-server-deployment.yml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ktunnel-server
  namespace: ktunnel
  labels:
    app: ktunnel-server
    component: server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ktunnel-server
  template:
    metadata:
      labels:
        app: ktunnel-server
        component: server
    spec:
      serviceAccountName: ktunnel-server
      containers:
      - name: ktunnel-server
        image: omrikiei/ktunnel:v1.6.1
        command: ["ktunnel"]
        args: 
          - "server"
          - "--port=8000"
          - "--verbose"
        ports:
        - containerPort: 8000
          name: ktunnel-port
          protocol: TCP
        env:
        - name: KTUNNEL_LOG_LEVEL
          value: "info"
        - name: KTUNNEL_PORT
          value: "8000"
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          tcpSocket:
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          tcpSocket:
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
            - ALL
      restartPolicy: Always
      terminationGracePeriodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: ktunnel-server-service
  namespace: ktunnel
  labels:
    app: ktunnel-server
    component: service
spec:
  selector:
    app: ktunnel-server
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
      name: ktunnel-api
  type: ClusterIP

```

---

## [namespace.yml](./namespace.yml)

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ktunnel
  labels:
    name: ktunnel
    app: ktunnel-server

```

---

## [rbac.yml](./rbac.yml)

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ktunnel-server
  namespace: ktunnel
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: ktunnel
  name: ktunnel-server
rules:
- apiGroups: [""]
  resources: ["services", "endpoints", "pods"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
- apiGroups: ["extensions", "networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ktunnel-server
  namespace: ktunnel
subjects:
- kind: ServiceAccount
  name: ktunnel-server
  namespace: ktunnel
roleRef:
  kind: Role
  name: ktunnel-server
  apiGroup: rbac.authorization.k8s.io

```

---

## [status.sh](./status.sh)

```bash
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

```

---

## [stop-tunnels.sh](./stop-tunnels.sh)

```bash
#!/bin/bash

# Stop all ktunnel processes
echo "🛑 Stopping all ktunnel tunnels..."

# Find and kill all ktunnel expose processes
PIDS=$(pgrep -f "ktunnel expose" 2>/dev/null || true)

if [ -z "$PIDS" ]; then
    echo "ℹ️  No active ktunnel tunnels found"
else
    echo "🔍 Found active tunnels (PIDs: $PIDS)"
    echo "$PIDS" | xargs kill
    
    # Wait a moment and check if they're really stopped
    sleep 2
    REMAINING=$(pgrep -f "ktunnel expose" 2>/dev/null || true)
    
    if [ -z "$REMAINING" ]; then
        echo "✅ All tunnels stopped successfully"
    else
        echo "⚠️  Some tunnels still running, force killing..."
        echo "$REMAINING" | xargs kill -9
        echo "✅ All tunnels force stopped"
    fi
fi

# Clean up log files
echo "🧹 Cleaning up log files..."
rm -f /tmp/ktunnel-*.log

echo "🎉 Tunnel cleanup completed!"

```

---
