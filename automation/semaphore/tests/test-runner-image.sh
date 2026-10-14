#!/bin/sh
set -eu
image=${1:?runner image required}
docker image inspect "$image" >/dev/null
docker run --rm --entrypoint sh "$image" -ec '
  test "$(id -u)" = 1001
  semaphore version | grep -F "v2.19.12"
  semaphore runner start --help | grep -F -- "--config"
  ansible --version | head -n 1 | grep -F "2.18.6"
  test ! -S /var/run/docker.sock
  test -w /tmp/semaphore
  test -w /home/semaphore
'
