#!/bin/sh
set -eu
if [ "${SSH_ORIGINAL_COMMAND-}" != 'host-audit' ]; then
    printf '%s\n' 'Only host-audit is permitted' >&2
    exit 2
fi
exec /usr/bin/sudo -n -u dungxbuif /usr/local/libexec/homelab-host-observer
