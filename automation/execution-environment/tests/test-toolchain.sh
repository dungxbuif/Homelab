#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
EE_DIR="$ROOT_DIR/automation/execution-environment"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

if [[ "${1:-}" == '--run' ]]; then
  command -v ansible >/dev/null || fail 'ansible is not installed'
  command -v tofu >/dev/null || fail 'tofu is not installed'
  command -v docker >/dev/null || fail 'docker is not installed'
  command -v yamllint >/dev/null || fail 'yamllint is not installed'
  command -v ansible-lint >/dev/null || fail 'ansible-lint is not installed'
  command -v shellcheck >/dev/null || fail 'shellcheck is not installed'
  ansible --version >/dev/null
  tofu version >/dev/null
  docker version --format '{{.Client.Version}}' >/dev/null 2>&1 || docker --version >/dev/null
  yamllint --version >/dev/null
  ansible-lint --version >/dev/null
  shellcheck --version >/dev/null
  printf 'execution-environment toolchain: ok\n'
  exit 0
fi

for required in Containerfile ansible-builder.yml requirements.txt requirements.yml; do
  test -f "$EE_DIR/$required" || fail "missing execution-environment/$required"
done
test -f "$ROOT_DIR/.gitlab-ci.yml" || fail 'missing .gitlab-ci.yml'

grep -Eq '^ARG ANSIBLE_CORE_VERSION=[0-9]+\.[0-9]+\.[0-9]+$' "$EE_DIR/Containerfile" \
  || fail 'ansible-core must be pinned in Containerfile'
grep -Eq '^ARG TOFU_VERSION=[0-9]+\.[0-9]+\.[0-9]+$' "$EE_DIR/Containerfile" \
  || fail 'OpenTofu must be pinned in Containerfile'
grep -Eq '^ARG DOCKER_CLI_VERSION=[0-9]+\.[0-9]+\.[0-9]+$' "$EE_DIR/Containerfile" \
  || fail 'Docker CLI must be pinned in Containerfile'

grep -Eq '^  - name: community\.docker$' "$EE_DIR/requirements.yml" \
  || fail 'community.docker collection is not declared'
grep -Eq '^  - name: community\.general$' "$EE_DIR/requirements.yml" \
  || fail 'community.general collection is not declared'
grep -Eq 'CI_COMMIT_SHA' "$ROOT_DIR/.gitlab-ci.yml" \
  || fail 'CI must publish immutable commit tags'
if grep -Eq '(^|[[:space:]])latest([[:space:]]|$|:)' "$ROOT_DIR/.gitlab-ci.yml"; then
  fail 'production CI must not use latest'
fi

printf 'execution-environment contract: ok\n'
