#!/usr/bin/env bash
set -euo pipefail

kubectl -n localstack get deploy,pod,svc,pvc
kubectl -n localstack exec deploy/localstack -- curl -fsS http://localhost:4566/_localstack/health
printf '\n'

