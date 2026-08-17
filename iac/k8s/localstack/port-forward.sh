#!/usr/bin/env bash
set -euo pipefail

kubectl -n localstack port-forward svc/localstack 4566:4566

