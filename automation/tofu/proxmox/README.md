# VM100 OpenTofu import boundary

This module is an unimported scaffold for VM100, not an approved live baseline.
Do not apply it: known hardware fields are now reconciled with read-only API
observations, but a live provider-generated no-op plan has not been verified. See the
[verified preflight](../../../docs/deployments/vm100-import-preflight-2026-10-14.md).
The table below contains observed values, not a completed import:

| Field | Value |
|---|---|
| Proxmox node | `pve` |
| VM ID | `100` |
| Proxmox name | `k8s-cp-1` (legacy label only; supply explicitly) |
| LAN | `10.10.0.31` |
| vCPU / RAM | `6` / `16384 MiB` |
| Root disk | `local-lvm`, `scsi0`, `200 GiB` |
| Bridge | `vmbr0` |

State and saved plans now enforce AES-GCM encryption through PBKDF2. A disposable
terraform_data fixture verifies encryption and correct/wrong/missing-key behavior
with OpenTofu 1.9.0, without using Proxmox credentials. Production state still
must not be created until secret-store injection and key recovery are verified.
Supply `TF_VAR_state_encryption_passphrase` from the executor secret store; never
store it in tfvars or Git. Keep the encryption provider/method names stable for
future decryption. Losing this key means losing access to encrypted state.
Move the state to the
private RustFS S3-compatible backend only after bucket versioning, credentials,
locking, and restore have been verified. The state must remain separate from
application data and must never be committed.

## Import workflow

Run through the pinned execution image and Semaphore `tofu-plan` template:

```bash
export TF_VAR_proxmox_api_token='provided by Semaphore only'
export TF_VAR_vm_name='k8s-cp-1'
# The executor must also inject TF_VAR_state_encryption_passphrase.
tofu init
tofu fmt -check
tofu validate
tofu plan -out=vm100.tfplan
```

The first plan must be strictly import-only, with no infrastructure delta. Any disk
replacement, network replacement, destroy, or unexpected VM recreation blocks
the workflow. After a Manager-approved import:

The initial import gate is stricter: it rejects every infrastructure mutation,
including in-place updates. Pipe the private JSON plan directly to the gate;
never publish raw JSON plans as CI artifacts because they can include secrets:

```bash
set -o pipefail
tofu show -json vm100.tfplan | python ../../scripts/check-vm100-plan.py --mode import
```

After the baseline is reconciled, encryption is tested, and the import is approved:

```bash
tofu apply vm100.tfplan
tofu plan -detailed-exitcode
```

The second plan must be no-op before CPU, RAM, disk, or swap policy changes are
managed. `prevent_destroy = true` is a guardrail, not a substitute for review.

Encryption protects files at rest, not the plaintext output of `tofu show -json`
or access by the running job. Pipe that output only to trusted validators and
never upload it as a public or unredacted job artifact.
