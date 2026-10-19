#!/usr/bin/env bash
# Scans every tracked file (docs/, monitoring/, deprecated/, *.md included).
# Reports rule + file:line only; matched values are never printed.
set -u

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P) || exit 2
repository=$(cd "${1:-.}" && pwd -P) || exit 2

exec python3 "$here/secret_scan.py" "$repository"
