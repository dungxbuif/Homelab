#!/bin/sh
set -eu

[ "$#" -eq 2 ] || { echo 'usage: scan-image.sh IMAGE REPORT_NAME' >&2; exit 2; }
image=$1
name=$2
case "$name" in
  ''|*[!a-z0-9_-]*) echo 'invalid report name' >&2; exit 2 ;;
esac
root=${CI_PROJECT_DIR:-$PWD}
root=$(cd "$root" && pwd)
reports="$root/security-reports"
umask 077
mkdir -p "$reports"
rm -f -- "$reports/$name.json"
work=$(mktemp -d "$root/.image-scan.XXXXXX")
container=
cleanup() {
  status=$?
  trap - EXIT
  if [ -n "$container" ]; then
    docker rm -f "$container" >/dev/null || status=1
  fi
  rm -rf -- "$work" || status=1
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Scan the local build, with no access to the daemon or registry login files.
docker image save --output "$work/image.tar" "$image"
# The scanner cannot bypass file permissions; the host directory stays 0700.
chmod 0444 "$work/image.tar"
container=$(docker create --user 65532:65532 --cap-drop ALL --security-opt no-new-privileges \
  --memory 1536m --cpus 1 \
  aquasec/trivy:0.76.0@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222 \
  image --input /tmp/image.tar --cache-dir /tmp/cache --scanners vuln \
  --severity HIGH,CRITICAL --exit-code 1 --exit-on-eol 1 \
  --ignorefile /dev/null --timeout 15m --parallel 2 --no-progress \
  --format json --output /tmp/report.json)
# API copies also work when the rootless daemon cannot traverse job-owned paths.
docker cp "$work/image.tar" "$container:/tmp/image.tar"
status=0
docker start --attach "$container" || status=$?
if ! docker cp "$container:/tmp/report.json" "$reports/$name.json"; then
  echo 'scanner report could not be retrieved' >&2
  [ "$status" -ne 0 ] || status=1
fi
[ "$status" -eq 0 ] || exit "$status"
[ -s "$reports/$name.json" ] || { echo 'scanner returned no report' >&2; exit 1; }
