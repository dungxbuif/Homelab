# Ansible host baseline

This tree is the active production inventory for the homelab control plane.
It intentionally contains only the public gateway, Pi5 manager/datastore, and
VM100 production worker. Kubernetes is not an active lab target.

## Safety boundary

- `playbooks/audit.yml` is read-only and may run without an apply approval.
- `playbooks/bootstrap.yml` fails unless `automation_apply_baseline=true` is
  explicitly supplied by an approved Semaphore job.
- Docker, Swarm membership, SSH, logging, and swap roles are disabled by
  default through `automation_manage_*` flags.
- The inventory contains transport addresses only. Application endpoints,
  passwords, API tokens, and SSH keys come from Semaphore credentials or the
  approved secret broker.
- The forced-command backup key remains separate from the `automation` user.

## Local validation

Run through the pinned execution environment:

```bash
ansible-inventory \
  --config automation/ansible/ansible.cfg \
  -i automation/ansible/inventories/production/hosts.yml --graph
docker run --rm --entrypoint ansible-playbook \
  -v "$PWD:/workspace" -w /workspace homelab-automation-ee:local \
  -i automation/ansible/inventories/production/hosts.yml \
  automation/ansible/playbooks/audit.yml --syntax-check
docker run --rm --entrypoint ansible-playbook \
  -v "$PWD:/workspace" -w /workspace homelab-automation-ee:local \
  -i automation/ansible/inventories/production/hosts.yml \
  automation/ansible/playbooks/bootstrap.yml --syntax-check
```

The first production run is audit-only. Baseline application follows the
approved order `vm100`, `pi5`, then `vps-gateway`, one host at a time, after
the restricted account and transport path have been verified.
