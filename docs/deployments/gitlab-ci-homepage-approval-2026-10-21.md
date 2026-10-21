# GitLab CI Homepage approval

Date: 2026-10-21

## Scope

GitLab CI now has a manual production job for the one application that is
already release-ready in the catalog: Homepage. The job is an approval surface,
not a general remote shell or arbitrary application deployer.

## Boundary

- `deploy:homepage-production` runs only on the default branch or a tag;
- the job targets the `production` environment and serializes it with
  `resource_group: homepage-production`; the environment must be marked
  protected in GitLab before live use;
- the digest is immutable and is checked by `automation/scripts/verify-deploy.sh`
  against the approved catalog entry;
- the SSH target is fixed to `homelab-homepage-release@10.10.0.5`;
- host identity comes from a protected file variable;
- the remote account accepts only `homepage-release sha256:<digest>` through its
  root-owned forced-command guard;
- the job sends the validated receipt through the existing Mezon notifier;
- no Docker socket, root key, registry credential, or database secret enters CI.

## Enrollment required

The GitLab project must define these as protected, masked/file variables before
the first live run:

```text
HOMELAB_HOMEPAGE_RELEASE_PRIVATE_KEY_FILE  (file variable)
HOMELAB_PI_KNOWN_HOSTS_FILE                (file variable)
HOMELAB_MEZON_WEBHOOK_URL_FILE            (file variable)
```

The first two files are the dedicated Homepage release key and the pinned Pi5
host key. The third file contains the existing Mezon webhook and must never be
echoed. The release script reads it only for the notifier process, so no
secret-bearing text variable is needed.
The environment named `production` must also be protected so only the intended
maintainer can click the manual job.

Until those variables and the protected environment are enrolled, the job is
intentionally fail-closed and A1 remains pending live acceptance.

## Verification

The 27 focused GitLab CI/deploy contract tests pass in an isolated Python
environment with `PyYAML`, and the release script passes `bash -n`. Live
acceptance still requires one successful manual job and one same-digest no-op,
with the Homepage route and Mezon receipt verified after each run.
