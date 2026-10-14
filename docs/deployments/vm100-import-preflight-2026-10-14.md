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
