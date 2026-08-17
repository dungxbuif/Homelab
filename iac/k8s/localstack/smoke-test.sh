#!/usr/bin/env bash
set -euo pipefail

kubectl -n localstack exec deploy/localstack -- sh -lc '
  set -e
  echo "hello localstack on k8s" > /tmp/localstack-k8s-smoke.txt
  awslocal s3 mb s3://saa-k8s-smoke-bucket 2>/dev/null || true
  awslocal s3 cp /tmp/localstack-k8s-smoke.txt s3://saa-k8s-smoke-bucket/hello.txt
  awslocal s3 ls s3://saa-k8s-smoke-bucket
'

