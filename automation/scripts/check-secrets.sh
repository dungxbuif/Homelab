#!/usr/bin/env bash
set -u

repository=$(cd "${1:-.}" && pwd -P) || exit 2
pattern='(glpat-[A-Za-z0-9_-]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|BEGIN [A-Z ]+ PRIVATE KEY)'

# Exit 1 alone means no matches; Git errors must never pass this gate.
git -c safe.directory="$repository" -C "$repository" grep -lI -E "$pattern" -- .
status=$?
case "$status" in
  0) printf '%s\n' 'Credential-like content found in tracked files above.' >&2; exit 1 ;;
  1) printf '%s\n' 'Tracked-file credential-pattern check passed.' ;;
  *) printf 'Credential check failed to execute (Git exit %s).\n' "$status" >&2; exit "$status" ;;
esac
