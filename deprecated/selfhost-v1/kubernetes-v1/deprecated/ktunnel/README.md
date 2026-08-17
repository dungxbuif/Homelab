# Ktunnel GitLab Setup

This directory contains configuration files for exposing a local GitLab instance (running in Docker) to the internet through Kubernetes using ktunnel.

## Overview

Ktunnel creates secure tunnels from your local GitLab Docker instance to your Kubernetes cluster, then exposes them through Traefik ingress routes. This allows you to:

- Access your local GitLab instance from anywhere via `https://gitlab.dungxbuif.com`
- Use the GitLab Container Registry via `https://registry.gitlab.dungxbuif.com`
- Access the ktunnel management interface via `https://ktunnel.dungxbuif.com`
- Connect via SSH for Git operations

## Prerequisites

1. **Kubernetes Cluster**: Running with Traefik as ingress controller
2. **Local GitLab**: GitLab running in Docker locally
3. **DNS Records**: Point the following domains to your Traefik load balancer:
   - `gitlab.dungxbuif.com`
   - `registry.gitlab.dungxbuif.com`
   - `ktunnel.dungxbuif.com`
4. **TLS Certificates**: Configured in Traefik for the above domains
5. **ktunnel Binary**: Download from [ktunnel releases](https://github.com/omrikiei/ktunnel/releases)

## Quick Deployment

### 1. Deploy to Kubernetes

Run the deployment script to set up all components:

```bash
chmod +x deploy.sh
./deploy.sh
```

### 2. Create Local Tunnels

After the Kubernetes deployment is ready, create tunnels from your local machine:

```bash
# Make sure your local GitLab is running on these ports:
# - Web interface: http://localhost:80
# - Container registry: http://localhost:5000

# Download and install ktunnel locally if not already done
wget https://github.com/omrikiei/ktunnel/releases/download/v1.6.1/ktunnel_1.6.1_Linux_x86_64.tar.gz
tar -xzf ktunnel_1.6.1_Linux_x86_64.tar.gz
sudo mv ktunnel /usr/local/bin/

# Create the tunnels
./create-tunnels.sh
```

## Manual Deployment Steps

If you prefer to deploy manually:

### 1. Deploy Kubernetes Components

```bash
# Create namespace
kubectl apply -f namespace.yml

# Set up RBAC permissions
kubectl apply -f rbac.yml

# Deploy ktunnel server
kubectl apply -f ktunnel-server-deployment.yml

# Create GitLab services and endpoints
kubectl apply -f gitlab-services.yml

# Set up ingress routes
kubectl apply -f gitlab-ingress.yml
```

### 2. Verify Deployment

```bash
# Check if all pods are running
kubectl get pods -n ktunnel

# Check services
kubectl get services -n ktunnel

# Check ingress routes
kubectl get ingressroutes -n ktunnel
kubectl get ingressroutetcp -n ktunnel
```

### 3. Create Local Tunnels

```bash
# Tunnel GitLab web interface (port 80)
ktunnel expose gitlab-web 80:80 -n ktunnel

# Tunnel GitLab registry (port 5000)
ktunnel expose gitlab-registry 5000:5000 -n ktunnel

# Optional: Tunnel SSH (port 22) if you need Git over SSH
ktunnel expose gitlab-ssh 22:22 -n ktunnel
```

## Configuration Files

- **`namespace.yml`**: Creates the ktunnel namespace
- **`rbac.yml`**: Sets up service account and permissions for ktunnel
- **`ktunnel-server-deployment.yml`**: Deploys the ktunnel server in Kubernetes
- **`gitlab-services.yml`**: Defines Kubernetes services and endpoints for GitLab
- **`gitlab-ingress.yml`**: Configures Traefik ingress routes for external access

## Local GitLab Configuration

Make sure your local GitLab Docker setup exposes the following ports:

```yaml
# docker-compose.yml example
services:
  gitlab:
    image: gitlab/gitlab-ce:latest
    ports:
      - "80:80"        # Web interface
      - "5000:5000"    # Container registry
      - "22:22"        # SSH (optional)
    # ... other configuration
```

## Troubleshooting

### Check Ktunnel Server Status

```bash
kubectl logs -n ktunnel deployment/ktunnel-server
kubectl get pods -n ktunnel
```

### Verify Tunnels

```bash
# List active tunnels
ktunnel list -n ktunnel

# Check tunnel status
kubectl get endpoints -n ktunnel
```

### Test Connectivity

```bash
# Test GitLab web access
curl -k https://gitlab.dungxbuif.com

# Test registry access
curl -k https://registry.gitlab.dungxbuif.com/v2/

# Test ktunnel management interface
curl -k https://ktunnel.dungxbuif.com
```

### Common Issues

1. **"Connection refused"**: Check if local GitLab is running and accessible on the specified ports
2. **"Service Unavailable"**: Verify ktunnel server is running and tunnels are established
3. **TLS errors**: Ensure certificates are properly configured in Traefik
4. **DNS issues**: Verify DNS records point to your Traefik load balancer

## Cleanup

To remove the ktunnel setup:

```bash
./cleanup.sh
```

Or manually:

```bash
kubectl delete namespace ktunnel
```

## Security Notes

- All traffic is encrypted using TLS
- Ktunnel creates secure tunnels between your local machine and Kubernetes
- Only specified ports are exposed through the tunnels
- Consider implementing additional authentication/authorization as needed