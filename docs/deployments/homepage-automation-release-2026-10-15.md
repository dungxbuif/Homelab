# Homepage automation release foundation

## Scope and decision

Start application delivery with Homepage, preserving live content and its
edge-http-net attachment. Do not use the old stack catalog's homelab-net entry
or deploy local image references as though they were published release images.
Production rollout requires a separate restricted Semaphore release action,
previous service-spec receipt, post-check and rollback. No live service was
changed during source/CI adoption.

The local app is `/Users/dungxbuif/workspace/homepage`. Its uncommitted legacy
single-production CI was preserved in local commit b40e428. The old main remains
at archive/pre-automation-main, and codex/automation-delivery preserves migration
work. Current main tracks a clean private GitLab history to avoid publishing old
CI credential history. No force-push or deletion of local history was used.

## Verified publication

- Project 5: `dungxbuif/homepage`, private. Initial clean commit:
  `01299fe7da4bb18aa3350b2fe39769da1bfea69e`, exported from reviewed source d80d43e.
- Runner 1 remains locked with exact project allow-list [2, 5]. No Docker socket,
  allowed-image, privilege or resource-boundary setting changed.
- Pipeline 39/job 83 succeeded. AMD64 image built, isolated HTTP output matched
  source byte-for-byte, nginx -t passed, then the image was pushed.
- Candidate:
  `registry-gitlab.dungxbuif.com/dungxbuif/homepage@sha256:c128afca4e026cfc4f33d4cf1c77adc8cb08f01215a3f2bde76a1ecca12b79fd`.
- Source index was compared directly with VM100 live source: no differences.
  The only reconciliation was the existing Stirling PDF shortcut missing locally.
- Three regression tests, source credential-pattern scan and YAML parse passed.
  Local ARM64 build and isolated HTTP smoke also passed. CI uses rootless DinD
  and the existing approved Docker job image; it performs no SSH or deployment.

The nginx base changed from a floating tag to a pinned observed 1.31.6 OCI index;
the redundant Node copy-only stage was removed. No JavaScript compilation or
application build mechanism was introduced. Production still runs its previous
image; release through Semaphore and recovery acceptance remain unfinished.
The app README describes the new delivery boundary; no public UI behavior changed.
