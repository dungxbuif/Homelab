#!/usr/bin/env bash
set -euo pipefail

for file in "$@"; do
  if grep -Eiq '(^|[^a-z])(password|token|private_key|client_secret|BEGIN [A-Z ]+PRIVATE KEY)([^a-z]|$)' "$file"; then
    echo "secret-like output detected in ${file}" >&2
    exit 1
  fi
done
echo "secret output scan: ok"
