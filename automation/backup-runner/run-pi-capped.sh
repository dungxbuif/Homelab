#!/usr/bin/env bash
set -euo pipefail

if (($# == 0)); then
  echo 'usage: run-pi-capped.sh COMMAND [ARG...]' >&2
  exit 2
fi

mode=${BACKUP_PI_RESOURCE_MODE:-portable}
nice_level=${BACKUP_PI_NICE:-10}
ionice_class=${BACKUP_PI_IONICE_CLASS:-3}
cpu_quota=${BACKUP_PI_CPU_QUOTA:-100%}
memory_max=${BACKUP_PI_MEMORY_MAX:-1G}
io_weight=${BACKUP_PI_IO_WEIGHT:-50}

[[ "$nice_level" =~ ^[0-9]+$ ]] || { echo 'BACKUP_PI_NICE must be a non-negative integer' >&2; exit 2; }
[[ "$ionice_class" =~ ^[0-3]$ ]] || { echo 'BACKUP_PI_IONICE_CLASS must be 0, 1, 2 or 3' >&2; exit 2; }
[[ "$cpu_quota" =~ ^[0-9]+%$ ]] || { echo 'BACKUP_PI_CPU_QUOTA must be a percentage' >&2; exit 2; }
[[ "$memory_max" =~ ^[0-9]+([KMG]i?B?)?$ ]] || { echo 'BACKUP_PI_MEMORY_MAX must be a byte value' >&2; exit 2; }
[[ "$io_weight" =~ ^[1-9][0-9]*$ ]] || { echo 'BACKUP_PI_IO_WEIGHT must be a positive integer' >&2; exit 2; }

case "$mode" in
  systemd)
    command -v systemd-run >/dev/null 2>&1 || {
      echo 'systemd-run is required for BACKUP_PI_RESOURCE_MODE=systemd' >&2
      exit 1
    }
    exec systemd-run --scope --quiet \
      -p "CPUQuota=$cpu_quota" \
      -p "MemoryMax=$memory_max" \
      -p "IOWeight=$io_weight" \
      -- "$@"
    ;;
  portable)
    command -v nice >/dev/null 2>&1 || { echo 'nice is required for portable resource mode' >&2; exit 1; }
    command -v ionice >/dev/null 2>&1 || { echo 'ionice is required for portable resource mode' >&2; exit 1; }
    exec nice -n "$nice_level" ionice -c "$ionice_class" -- "$@"
    ;;
  *)
    echo "unsupported BACKUP_PI_RESOURCE_MODE: $mode" >&2
    exit 2
    ;;
esac
