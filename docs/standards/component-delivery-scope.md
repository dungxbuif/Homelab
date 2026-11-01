---
type: Standard
title: Component Delivery Scope
description: Decide which components require the lab CI/CD flow and which remain external clients or source-only components
status: stable
generated:
  by: codex
  at: "2026-11-01T01:20:00+07:00"
stale_after: "2027-01-30T01:20:00+07:00"
tags:
- ci
- cd
- components
- release
---

# Component Delivery Scope

The lab CI/CD standard applies to a component that runs inside the lab. It does
not apply automatically to every directory or artifact in the same repository.
This is a component-level decision, recorded in the Homelab project document
and, when the repository has a deployment manifest, in its `app.yml`.

## Component classes

| Class | Where it runs | Lab CI/CD requirement | Release evidence |
|---|---|---|---|
| `lab-runtime` | Swarm, Compose, a lab VM, Pi5, VPS or another managed lab host | Required: test, scan, build, registry push, environment promotion, deploy, health check and rollback | Commit, pipeline, immutable image/artifact digest, environment, health result and rollback pointer |
| `external-client` | Owner-controlled Mac, phone, desktop or other device outside lab runtime | No lab deploy pipeline. Use the repository's local/platform release procedure when a client build is needed | Source revision, client version/build, configuration contract and manual verification record when released |
| `source-only` | Library, documentation, experiment or build input with no deployed runtime | No lab deploy pipeline | Tests or review evidence appropriate to the repository |

One repository may contain more than one class. The class is attached to the
component, so a client folder does not silently become a lab deployment just
because the proxy or server in the same repository is deployed in the lab.

## Mac OCR decision — 2026-11-01

Mac OCR is a mixed repository:

| Component | Class | Decision |
|---|---|---|
| `proxy/`, embedded admin UI/docs and root `Dockerfile` | `lab-runtime` | Enroll in the lab CI/CD flow. Build the Linux proxy image, publish it to the canonical registry, promote the same digest through environments, deploy the Swarm service at one replica, run `/healthz` and `/readyz` plus proxy API smoke tests, and retain rollback evidence. |
| `native/` Mac OCR Native app | `external-client` | Excluded from the lab CI/CD deploy flow. Build and install it on the Mac through the repository's local release procedure. Keep its proxy URL, transport, auth and API compatibility documented. |
| `omniscan/` | `source-only` / retired in the lab | No delivery enrollment until a separate owner decision changes its lifecycle. |

Changing `native/` does not trigger a proxy deploy. Changing the proxy, its
embedded admin/docs assets, the Dockerfile or its runtime contract does trigger
the proxy pipeline. A proxy release records whether client compatibility was
checked; that check does not build or deploy the native app.

The native app still follows the repository Git flow and documentation rules.
If it is released, its version/build and manual Mac verification are recorded
in the repository release notes and the Homelab project doc. It does not receive
`dev` → `staging` → `prod` environment promotion tags because it is not a lab
runtime component.

## Generic lab flow

For every `lab-runtime` component:

1. Merge the tested change into the repository's declared release branch
   (`main`, `master` or `prod`); verify the integrated commit on the required
   remotes.
2. Build once and publish an immutable digest to the lab registry.
3. Promote that digest with the lab tag convention
   `<env>-<major>.<minor>.<patch>[-<prerelease>]`.
4. Deploy through protected GitLab environments, inject runtime configuration
   and secrets, and run component-specific health and functional smoke tests.
5. Record the deployment receipt and update the repository and Homelab docs.
6. Roll back to the previous digest/configuration when the gate fails.

For `external-client` and `source-only` components, the repository's Git flow,
review, documentation and release trace remain required. The lab deploy stages
are simply omitted because there is no lab runtime to deploy.

## Required declaration

The target `app.yml` shape is illustrative until its policy parser is enrolled:

```yaml
components:
  proxy:
    delivery_scope: lab-runtime
    paths: [Dockerfile, proxy/**, proxy/admin-ui/**, docs-site/**, docs/**]
    artifact: container
    deploy: swarm
  native:
    delivery_scope: external-client
    paths: [native/**]
    artifact: macos-app
    deploy: manual-client
```

Until this declaration exists in the deployment repository, the project doc is
the authoritative classification. An unclassified component cannot be
promoted to production.

