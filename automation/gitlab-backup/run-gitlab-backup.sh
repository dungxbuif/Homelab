#!/usr/bin/env bash
set -euo pipefail

# This wrapper runs on VM100 and never stops, scales, or recreates GitLab.
output=${1:?usage: run-gitlab-backup.sh OUTPUT_DIR}
expected_version=${GITLAB_EXPECTED_VERSION:-18.11.11}
container_pattern=${GITLAB_CONTAINER_PATTERN:-gitlab_gitlab}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$output"
tmp="$output/.incomplete"
[[ ! -e "$output/complete" ]] || { echo "completed output already exists: $output/complete" >&2; exit 1; }
rm -rf "$tmp"
mkdir -p "$tmp"

container=$(docker ps --filter "name=${container_pattern}" --filter status=running --format '{{.Names}}' | head -n1)
[[ -n "$container" ]] || { echo 'healthy GitLab container not found' >&2; exit 1; }
version=$(docker exec "$container" cat /opt/gitlab/embedded/service/gitlab-rails/VERSION)
[[ "$version" == "$expected_version" ]] || {
  echo "GitLab version mismatch: expected ${expected_version}, found ${version}" >&2
  exit 1
}

docker exec "$container" gitlab-backup create STRATEGY=copy >/dev/null
native_source=$(docker exec "$container" sh -c 'find /var/opt/gitlab/backups -maxdepth 1 -type f -name "*_gitlab_backup.tar" -printf "%T@ %p\\n" | sort -nr | head -n1 | cut -d" " -f2-')
[[ -n "$native_source" ]] || { echo 'GitLab native archive not found' >&2; exit 1; }
docker cp "$container:$native_source" "$tmp/gitlab-native-backup.tar"

docker exec "$container" gitlab-ctl backup-etc --backup-path /var/opt/gitlab/backups >/dev/null
config_source=$(docker exec "$container" sh -c 'find /var/opt/gitlab/backups -maxdepth 1 -type f -name "gitlab_config_*.tar" -printf "%T@ %p\\n" | sort -nr | head -n1 | cut -d" " -f2-')
[[ -n "$config_source" ]] || { echo 'GitLab config archive not found' >&2; exit 1; }
docker cp "$container:$config_source" "$tmp/gitlab-config-secrets.tar"

# The Omnibus native backup does not make local registry storage independently
# recoverable. Capture it as a separate online archive; immutable blobs remain
# content-addressed while the GitLab registry is serving traffic.
docker exec "$container" sh -c 'tar --xattrs --numeric-owner -C /var/opt/gitlab -cf - registry' | gzip -1 > "$tmp/gitlab-local-registry.tar.gz"

postgres_server_version=$(tar -xOf "$tmp/gitlab-native-backup.tar" db/database.sql.gz | gzip -dc | sed -n 's/^-- Dumped from database version //p' | head -n1 | sed 's/ .*//')
pg_dump_version=$(docker exec "$container" /opt/gitlab/embedded/bin/pg_dump --version | sed -n 's/.*) //p')

python3 "$script_dir/coverage-manifest.py" \
  --output "$tmp/manifest.json" \
  --version "$version" \
  --native "$tmp/gitlab-native-backup.tar" \
  --config "$tmp/gitlab-config-secrets.tar" \
  --registry "$tmp/gitlab-local-registry.tar.gz" \
  --postgres-server-version "$postgres_server_version" \
  --pg-dump-version "$pg_dump_version"

printf '%s\n' "$version" > "$tmp/gitlab-version"
(
  cd "$tmp"
  sha256sum gitlab-native-backup.tar gitlab-config-secrets.tar gitlab-local-registry.tar.gz gitlab-version > checksums.sha256
)
printf '%s\n' "$(basename "$output")" > "$tmp/COMPLETE"
mv "$tmp" "$output/complete"
printf '%s\n' "$output/complete"
