#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

make_database_run() {
  local name=$1
  mkdir -p "$tmp/runs/$name"
  printf '%s\n' "$name" > "$tmp/runs/$name/COMPLETE"
}

make_gitlab_run() {
  local name=$1
  mkdir -p "$tmp/runs/$name/complete"
  printf '%s\n' "$name" > "$tmp/runs/$name/complete/COMPLETE"
}

for name in databases-20261006-010000 databases-20261006-020000 databases-20261006-030000; do
  make_database_run "$name"
done
mkdir -p "$tmp/runs/.databases-20261006-000000.incomplete"
printf 'unfinished\n' > "$tmp/runs/.databases-20261006-000000.incomplete/data"

for name in gitlab-20261006-010000 gitlab-20261006-020000 gitlab-20261006-030000; do
  make_gitlab_run "$name"
done

env BACKUP_STAGING_ROOT="$tmp/runs" BACKUP_LOCAL_RUN_KEEP=2 \
  bash "$root/scripts/cleanup-local-runs.sh" databases
env BACKUP_STAGING_ROOT="$tmp/runs" BACKUP_LOCAL_RUN_KEEP=2 \
  bash "$root/scripts/cleanup-local-runs.sh" gitlab

test -d "$tmp/runs/databases-20261006-030000"
test -d "$tmp/runs/databases-20261006-020000"
test ! -e "$tmp/runs/databases-20261006-010000"
test -d "$tmp/runs/.databases-20261006-000000.incomplete"
test -d "$tmp/runs/gitlab-20261006-030000"
test -d "$tmp/runs/gitlab-20261006-020000"
test ! -e "$tmp/runs/gitlab-20261006-010000"

echo 'local retention tests passed'
