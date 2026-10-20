#!/usr/bin/env bash
set -euo pipefail

class=${1:?usage: cleanup-local-runs.sh databases|database-instances|rustfs|gitlab|configs}
case "$class" in
  databases|database-instances|rustfs|gitlab|configs) ;;
  *) echo "unsupported backup class: $class" >&2; exit 2 ;;
esac

staging_root=${BACKUP_STAGING_ROOT:-/ssd-data/infra/backups/homelab}
keep=${BACKUP_LOCAL_RUN_KEEP:-2}
[[ "$keep" =~ ^[1-9][0-9]*$ ]] || {
  echo 'BACKUP_LOCAL_RUN_KEEP must be a positive integer' >&2
  exit 2
}

[[ -d "$staging_root" ]] || {
  echo "local staging root does not exist; nothing to clean: $staging_root"
  exit 0
}
staging_root=$(cd -- "$staging_root" && pwd)

is_complete() {
  local run_dir=$1
  if [[ "$class" == gitlab ]]; then
    [[ -f "$run_dir/complete/COMPLETE" ]]
  else
    [[ -f "$run_dir/COMPLETE" ]]
  fi
}

completed=()
for run_dir in "$staging_root/$class-"*; do
  [[ -d "$run_dir" && ! -L "$run_dir" ]] || continue
  is_complete "$run_dir" || continue
  completed+=("$run_dir")
done

completed_count=${#completed[@]}
if ((completed_count > 0)); then
  sorted=$(printf '%s\n' "${completed[@]}" | sort -r)
else
  sorted=''
fi

removed=0
kept=0
while IFS= read -r run_dir; do
  [[ -n "$run_dir" ]] || continue
  if ((kept < keep)); then
    kept=$((kept + 1))
    continue
  fi
  case "$run_dir" in
    "$staging_root/$class-"*) ;;
    *) echo "refusing unexpected cleanup path: $run_dir" >&2; exit 1 ;;
  esac
  rm -rf -- "$run_dir"
  removed=$((removed + 1))
  printf 'removed local staging: %s\n' "$run_dir"
done <<< "$sorted"

printf 'local staging class=%s completed=%s kept=%s removed=%s; incomplete runs preserved\n' \
  "$class" "$completed_count" "$kept" "$removed"
