# Webhook Relay Kubernetes Deployment Guide

This guide provides step-by-step instructions to deploy Webhook Relay on your Kubernetes cluster with persistent storage for databases.

## Prerequisites

- Kubernetes cluster with kubectl access
- Longhorn storage class available
- Access to create namespaces and deploy resources

## Deployment Steps

### 1. Create the namespace

```bash
kubectl apply -f namespace.yml
```

### 2. Deploy PostgreSQL and Redis with persistent storage

```bash
kubectl apply -f database.yml
```

### 3. Apply ConfigMap and Secrets

```bash
kubectl apply -f webhook-relay-configmap.yml
kubectl apply -f webhookrelay-secrets.yml
```

### 4. Deploy Webhook Relay core components

```bash
kubectl apply -f deployment.yml
kubectl apply -f service.yml
kubectl apply -f ingress.yml
```

### 5. Enable auto-scaling with HPA

```bash
kubectl apply -f hpa.yml
```

## Quick Start

To deploy the entire application in one go:

```bash
kubectl apply -f namespace.yml
kubectl apply -f database.yml
kubectl apply -f webhook-relay-configmap.yml
kubectl apply -f webhookrelay-secrets.yml
kubectl apply -f deployment.yml
kubectl apply -f service.yml
kubectl apply -f ingress.yml
kubectl apply -f hpa.yml
```

## Monitoring Deployment Progress

### Check pod status

```bash
# Watch pods coming online
kubectl get pods -n webhookrelay -w
```

### Verify database readiness

```bash
# Check if PostgreSQL is ready
kubectl get pods -n webhookrelay -l app=postgres

# Check if Redis is ready
kubectl get pods -n webhookrelay -l app=redis
```

### Verify webhook-relay deployment status

```bash
# Check deployment status
kubectl rollout status deployment/transponder -n webhookrelay

# Check application logs
kubectl logs -n webhookrelay deployment/transponder
```

## Testing the Setup

### Database connectivity tests

```bash
# Test PostgreSQL connection
kubectl run -n webhookrelay postgres-client --rm --tty -i --restart='Never' \
  --image postgres:16.1 --env="PGPASSWORD=<DEPRECATED_WEBHOOK_RELAY_POSTGRES_PASSWORD>" \
  -- psql -h postgres -U webhookrelay -d webhookrelay -c '\l'

# Test Redis connection
kubectl run -n webhookrelay redis-client --rm --tty -i --restart='Never' \
  --image redis:7.2.4 -- redis-cli -h redis -a <DEPRECATED_WEBHOOK_RELAY_REDIS_PASSWORD> ping
```

### Access the application

Once deployed, access the Webhook Relay dashboard at:
```
https://webhookrelay.dungxbuif.com
```

## Troubleshooting Common Issues

### Pod start failures

```bash
# Check pod status and events
kubectl describe pod -n webhookrelay $(kubectl get pod -n webhookrelay -l app=transponder -o jsonpath='{.items[0].metadata.name}')
```

### Database connection issues

```bash
# Check PostgreSQL logs
kubectl logs -n webhookrelay $(kubectl get pod -n webhookrelay -l app=postgres -o jsonpath='{.items[0].metadata.name}')

# Check Redis logs
kubectl logs -n webhookrelay $(kubectl get pod -n webhookrelay -l app=redis -o jsonpath='{.items[0].metadata.name}')
```

## Complete Cleanup

If you need to remove the entire deployment:

```bash
kubectl delete -f hpa.yml
kubectl delete -f ingress.yml
kubectl delete -f service.yml
kubectl delete -f deployment.yml
kubectl delete -f webhook-relay-configmap.yml
kubectl delete -f webhookrelay-secrets.yml
kubectl delete -f database.yml
kubectl delete -f namespace.yml
```