#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
kubectl apply -f namespace.yaml
kubectl apply -f pvc.yaml -f deployment.yaml -f service.yaml -f ingress.yaml
kubectl -n localstack rollout status deploy/localstack --timeout=180s
