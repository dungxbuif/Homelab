#!/usr/bin/python3 -I
"""Restrict the release identity to one digest argument, without a shell."""
import os
import re
import sys


def main():
    command = os.environ.get('SSH_ORIGINAL_COMMAND', '')
    match = re.fullmatch(r'homepage-release (sha256:[a-f0-9]{64})', command)
    if len(sys.argv) != 1 or match is None:
        print('Only an approved Homepage digest release is permitted', file=sys.stderr)
        return 2
    os.execve('/usr/bin/sudo.ws',
              ['/usr/bin/sudo.ws', '-n', '-u', 'dungxbuif',
               '/usr/local/libexec/homelab-homepage-release', match.group(1)],
              {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'})


if __name__ == '__main__':
    sys.exit(main())
