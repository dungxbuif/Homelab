# VM100 import preflight

Read-only Proxmox API confirms VM100 is running on pve with 6 cores, 16384 MiB
RAM and 200 GiB scsi0 on local-lvm. Its Proxmox name is still `k8s-cp-1`; this is
a stale VM label, not an active Kubernetes deployment. Guest hostname is separate.
Actual config: protection=0, ostype=other, scsihw=virtio-scsi-pci, onboot=1,
balloon=0, CPU host, one socket, agent=1, BIOS seabios. scsi0 has discard=on,
replicate=0 and no iothread option. net0 has virtio MAC 8E:8D:DC:BD:7F:72 on vmbr0.
Cloud-init media remains attached as ide2. Existing Terraform defaults differ in
name, description, protection, OS and iothread; do not apply this guessed baseline.

Before further import work, add a fail-closed JSON plan gate: only VM100 no-op
actions are allowed, with exactly pve/100 for import mode; reject updates,
replacement, deletion, creation, deferred/errored/incomplete plans and unexpected
resources. Empty or malformed input must fail. Never print full plan contents,
which can include secrets. Test every rejection path. This does not replace
matching the actual provider schema, encrypting state, or reviewing a live plan.

## Semaphore plan artifact contract, 2026-10-16

The Semaphore template contract now treats a plan as an artifact bundle rather
than only a saved binary. `tofu-plan` requires a caller-selected
`plan_artifact_id`, writes the binary `artifacts/vm100.tfplan`, the human review
text `artifacts/vm100.plan.txt`, the private raw JSON
`artifacts/vm100.plan.json`, its SHA-256 value, and
`artifacts/vm100.plan.manifest.json`. The post-check requires every member of
the bundle and runs `check-vm100-plan.py --mode import` against the JSON. Raw
plan JSON can contain secrets and must remain a private Semaphore artifact.

`tofu-apply-approved` accepts `approved_plan_id` and
`approved_plan_hash`. Before invoking `tofu apply`, it verifies that the
approved ID and hash match the plan manifest and the binary SHA-256, verifies
that the saved text/JSON views still describe the binary, and reruns the
import-only JSON gate. A mismatch exits before `apply` and creates no binding
receipt. A matching approval creates the private
`artifacts/vm100-approved-plan.json` receipt containing the approved ID and
hash; the post-check also records the detailed-exitcode plan output in
`artifacts/vm100-post-apply.txt`.

This is a source contract only. It does not enroll a live Semaphore template,
call Proxmox, create state, or authorize an import/apply. Local contract tests
use a fake `tofu` executable and the checked-in JSON gate; the real provider
and production credentials are deliberately not involved.

## Live read-only provider preflight on 2026-10-16

Using the pinned `homelab-automation-ee:local` image, the pinned Proxmox CA,
the existing scoped API token from the local credential store, and a disposable
preflight encryption passphrase, the provider successfully connected to
`https://pve:8006/` mapped to `10.10.0.20`. `tofu validate` passed and the live
provider plan reported exactly:

```text
Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.
```

The plan was written only inside the disposable container and was not applied.
No Proxmox state, VM configuration, disk, network, or cloud-init value was
changed. The certificate was verified with `SSL_CERT_FILE`; TLS bypass remained
false. This proves the provider/import baseline, not production state recovery.
The next gate is to inject a separately escrowed recoverable state key into the
controlled Semaphore executor, bind the reviewed plan artifact, and obtain the
required Manager approval before the first import/apply.

API read used the existing private endpoint and legacy token without mutation;
the current endpoint uses a self-signed certificate and TLS verification was
disabled for that bootstrap read. A trusted CA and scoped controller credential
are still needed before the final production workflow. No import/apply occurred.

Implemented the strict plan gate in `automation/scripts/check-vm100-plan.py`.
Eight tests pass both locally and in the pinned local execution image, including
unknown target identity and all mutating action classes. CI now invokes the test.
The module has its own ignore rules for `.state`, plan/state files and tfvars;
the root ignore patterns previously missed `.state/vm100.tfstate`.
The README explicitly labels this as an unimported, unencrypted scaffold. The
guard has NOT yet inspected a real provider-generated plan, and does not prove
the import is complete or the state backend is ready.

Next: enforce AES-GCM state and saved-plan encryption with a PBKDF2 key provider.
The passphrase has no default and must be injected by the controlled executor;
never write it into tfvars or Git. Validate encryption with real OpenTofu 1.9.0
against a disposable built-in terraform_data resource only: correct-key decrypt,
wrong/missing-key rejection, and no plaintext marker in state or saved plan.
No Proxmox token, provider, import or production resource is used by that test.
Production key escrow/recovery and secret-store integration remain required.

Encryption fixture now passes with real OpenTofu 1.9.0: saved plan/state omit
the plaintext marker, correct-key reads succeed, wrong/empty/missing-key reads
fail. Provider `bpg/proxmox` 0.116.0 initialization with backend disabled succeeds;
`tofu validate` and `tofu fmt -check` also pass. No production key was created,
no real state/plan was written, and no Proxmox import/apply was executed. These
checks validate implementation mechanics, not the live baseline or key recovery.

## Baseline reconciliation on 2026-10-15

A fresh read-only config request confirms the same hardware and legacy name.
Remove the guessed VM name default (require the observed name as input), remove
the invented description, and match observed protection=false, OS=other,
scsi controller, disk replication/iothread flags, MAC and attached cloud-init
interface. Keep prevent_destroy. Do not rename the VM or enable protection during
import; those are separate reviewed changes after an import-only/no-op plan.
Provider schema validation is not proof of a no-op live plan; legacy boot mapping,
trusted TLS, scoped API credential and state key escrow still need completion
before import/apply. The observed cloud-init DNS, static IP, Ubuntu account and
SSH key are now declared explicitly. Proxmox reports `ostype=other`, but provider
0.116.0 does not round-trip that imported field into resource state, so the OS
block remains intentionally unmanaged during import. Proxmox masks the existing
`cipassword` on read, so the module ignores only that single sensitive nested
attribute; it never ignores the full initialization block or any
hardware/network field. A password rotation remains a separate, explicit
operation.
Use the pinned provider's documented field names:
https://github.com/bpg/terraform-provider-proxmox/blob/v0.116.0/docs/resources/virtual_environment_vm.md

The reconciled module passes `tofu fmt`, `tofu validate` with the initialized
pinned provider, the VM100 contract test, two observed-baseline regression tests,
and all eight strict import-plan tests. The next live preflight must prove the
provider plan is import-only; an in-place update or any destroy/replacement still
blocks approval. No API mutation, provider import, production state, saved live
plan or apply was performed.
The operator was asked where the independent state encryption recovery key
should be escrowed; bootstrap can continue elsewhere while that is decided.

## Controller transport hardening

Before this change, the unused scaffold defaulted `proxmox_tls_insecure` to true
and enabled the operator SSH agent. Before any controller enrollment, make TLS verification
the default and disable agent inheritance. This does not establish certificate
trust or create a scoped credential; it ensures those missing prerequisites
fail visibly instead of silently weakening transport. Keep the known hardware
baseline and import-only gate unchanged. Verify defaults with regression tests,
format/schema validation, and the existing import-plan tests. No live provider
plan, import, VM mutation or state key creation is authorized by this change.
Public app docs are unaffected; update the operator README.

Implemented: TLS bypass now defaults to false and SSH agent use is explicitly
false. The new regression failed before the change, then passed. All 12 module
tests pass in the execution image, including real disposable encrypted-state
tests and strict import-plan rejection tests. `tofu fmt -check` and initialized
provider `tofu validate` pass. Review found no blockers. No live plan/import,
certificate trust change, credential creation or VM mutation occurred.
