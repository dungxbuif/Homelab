#!/usr/bin/env bash
# Fails when a captured output file contains secret-like content. Never prints matches.
set -euo pipefail

for file in "$@"; do
  if grep -Eiq '(^|[^a-z])(password|token|private_key|client_secret|BEGIN [A-Z ]+PRIVATE KEY)([^a-z]|$)' "$file"; then
    echo "secret-like output detected in ${file}" >&2
    exit 1
  fi
  if grep -Eiq '(authorization:[[:space:]]*basic[[:space:]]+[A-Za-z0-9+/=]{8,}|curl .*[[:space:]]-u[[:space:]]+[A-Za-z_][A-Za-z0-9_.-]*:[^[:space:]$<]+|default_token[[:space:]]*=[[:space:]]*"?[A-Za-z0-9]{6,})' "$file"; then
    echo "credential-bearing output detected in ${file}" >&2
    exit 1
  fi
done
echo "secret output scan: ok"
