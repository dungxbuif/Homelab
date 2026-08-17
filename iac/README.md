# Proxmox Kubernetes IaC Runbook

This directory is the automation entrypoint for building a demo Kubernetes HA control-plane on Proxmox.

Related system docs:

- Root homelab overview: [`../index.md`](../index.md)
- System context playbook: [`../docs/MAIN.md`](../docs/MAIN.md)
- **Prerequisites Guide (Start Here): [`./PRE_REQUIRE.md`](./PRE_REQUIRE.md)**
- Original IaC design spec: [`../docs/superpowers/specs/2026-05-29_k8s_proxmox_iac_design.md`](../docs/superpowers/specs/2026-05-29_k8s_proxmox_iac_design.md)

Target architecture:

- Proxmox creates 3 Ubuntu cloud-init VMs.
- All 3 VMs are Kubernetes control-plane nodes.
- `kubeadm` bootstraps a stacked-etcd cluster.
- `kube-vip` provides a stable API virtual IP.
- Ansible configures the operating system, container runtime, Kubernetes packages, kube-vip, and CNI.

Current state:

- `create_template.sh` exists and creates an Ubuntu cloud-init template.
- `terraform/` exists and creates 3 VMs from that template.
- `ansible/` scaffold exists for common OS prep, containerd, Kubernetes packages, kube-vip, CNI, and verification.

## Architecture

Recommended demo addressing:

| Role | Hostname | IP |
|---|---:|---:|
| API VIP | `k8s-api-vip` | `<K8S_VIP>` |
| Control Plane 1 | `k8s-cp-1` | `<K8S_CP1_IP>` |
| Control Plane 2 | `k8s-cp-2` | `<K8S_CP2_IP>` |
| Control Plane 3 | `k8s-cp-3` | `<K8S_CP3_IP>` |
| Gateway | MikroTik | `<MIKROTIK_IP>` |

ASCII topology:

```text
                           Homelab LAN: <LAN_SUBNET>

        +-------------------------------------------------------+
        | MikroTik hEX S                                       |
        | Gateway: <MIKROTIK_IP>                                   |
        | DHCP must reserve/exclude <K8S_VIP>-33              |
        +--------------------------+----------------------------+
                                   |
                                   | vmbr0 / Proxmox bridge
                                   v
        +-------------------------------------------------------+
        | Proxmox host                                          |
        |                                                       |
        |  +-------------------+                                |
        |  | k8s-cp-1          |                                |
        |  | <K8S_CP1_IP>        |<---------+                     |
        |  | kube-apiserver    |          |                     |
        |  | etcd              |          |                     |
        |  +-------------------+          |                     |
        |                                 | kube-vip ARP leader |
        |  +-------------------+          | advertises          |
        |  | k8s-cp-2          |          | <K8S_VIP>:6443     |
        |  | <K8S_CP2_IP>        |<---------+                     |
        |  | kube-apiserver    |                                |
        |  | etcd              |                                |
        |  +-------------------+                                |
        |                                                       |
        |  +-------------------+                                |
        |  | k8s-cp-3          |<---------+                     |
        |  | <K8S_CP3_IP>        |          |                     |
        |  | kube-apiserver    |          |                     |
        |  | etcd              |          |                     |
        |  +-------------------+          |                     |
        +-------------------------------+-+---------------------+
                                        |
                                        v
                              API VIP <K8S_VIP>
                              kubeadm endpoint :6443

Future app ingress:

  Pi Caddy -> K8s ingress/LB IP, recommended pool <K8S_INGRESS_POOL_START>-49
```

The kubeadm endpoint should be:

```text
<K8S_VIP>:6443
```

Flow:

```text
kubectl / kubelet / join nodes
  -> <K8S_VIP>:6443
  -> kube-vip advertises VIP from one healthy control-plane node
  -> local kube-apiserver
```

If the node holding `<K8S_VIP>` fails, kube-vip moves the VIP to another control-plane node.

## Why kube-vip

kube-vip is preferred here over a standalone HAProxy VM because this is a compact homelab demo cluster.

Benefits:

- No extra load balancer VM required.
- Avoids a single HAProxy node becoming the API single point of failure.
- Works well for bare-metal/Proxmox clusters.
- Can later support Kubernetes `LoadBalancer` services if configured for that mode.

Tradeoff:

- It is Kubernetes-specific infrastructure.
- External HAProxy + Keepalived is still useful when practicing traditional external LB architecture.

## Repository Layout

Existing:

```text
iac/
  create_template.sh
  terraform/
    main.tf
    variables.tf
    .env
```

Recommended target layout:

```text
iac/
  README.md
  create_template.sh
  terraform/
    main.tf
    variables.tf
    outputs.tf
    terraform.tfvars.example
  ansible/
    site.yml
    inventory.ini
    group_vars/
      all.yml
      k8s.yml
    roles/
      common/
      containerd/
      kubernetes/
      kube_vip/
      cni/
      verify/
```

## Prerequisites

Local machine:

- Terraform or OpenTofu.
- Ansible.
- SSH access to the Proxmox host.
- Proxmox API token.
- SSH public key for cloud-init.

Proxmox:

- Working bridge, expected `vmbr0`.
- Storage, currently expected `local-lvm`.
- Ubuntu cloud-init template, default name `ubuntu-22.04-template`.
- VM IDs available for the 3 Kubernetes nodes.

Network:

- LAN subnet: `<LAN_SUBNET>`.
- Gateway: `<MIKROTIK_IP>`.
- DNS: preferably `<PI_IP>` and `1.1.1.1`.
- Reserve IPs `<K8S_VIP>-33` in MikroTik DHCP or ensure they are outside DHCP pool.

## Step 1: Create The Proxmox Template

Run `create_template.sh` on the Proxmox host as root:

```bash
cd /path/to/Homelab/iac
scp create_template.sh root@<proxmox-ip>:/root/create_template.sh
ssh root@<proxmox-ip>
bash /root/create_template.sh
```

Current script behavior:

- Downloads Ubuntu 22.04 cloud image.
- Creates VM ID `9000`.
- Imports disk into `local-lvm`.
- Adds cloud-init drive.
- Enables serial console.
- Converts the VM to template named `ubuntu-22.04-template`.

Recommended future improvements:

- Install or enable `qemu-guest-agent`.
- Add base packages useful for automation.
- Make VM ID, storage, bridge, Ubuntu version, and image path configurable.
- Consider Ubuntu 24.04 LTS once Kubernetes package compatibility is confirmed.

## Step 2: Configure Terraform

Create a local tfvars file from a future example file:

```bash
cd iac/terraform
cp terraform.tfvars.example terraform.tfvars
```

Expected values:

```hcl
pm_api_url          = "https://<proxmox-host>:8006/api2/json"
pm_api_token_id     = "terraform@pve!homelab"
pm_api_token_secret = "<secret>"

proxmox_host = "pve"
template_name = "ubuntu-22.04-template"
nic_name = "vmbr0"
gw_ip = "<MIKROTIK_IP>"
ssh_public_key = "ssh-ed25519 ..."
```

Do not commit `terraform.tfvars` or `.env`.

## Step 3: Create The VMs

Current Terraform already creates 3 VMs:

```bash
cd iac/terraform
terraform init
terraform plan
terraform apply
```

Current VM defaults:

- 3 nodes.
- 2 vCPU.
- 4GB RAM.
- 30GB disk.
- Network model `virtio`.
- Bridge from `var.nic_name`, default `vmbr0`.
- IPs:
  - `<K8S_CP1_IP>`
  - `<K8S_CP2_IP>`
  - `<K8S_CP3_IP>`

Recommended Terraform improvements:

- Add variables for CPU, memory, disk, storage, VM ID base, DNS, and IP list.
- Add `ciuser`.
- Add `nameserver`.
- Add `ipconfig0` from a structured node map instead of string interpolation.
- Add outputs for Ansible inventory.
- Add tags/descriptions so VMs are easy to identify in Proxmox.

## Step 4: Ansible Bootstrap Plan

Ansible should own OS and Kubernetes configuration.

Role: `common`

- Set hostname.
- Configure `/etc/hosts`.
- Update apt cache.
- Install base tools.
- Disable swap.
- Load kernel modules:
  - `overlay`
  - `br_netfilter`
- Set sysctl:
  - `net.bridge.bridge-nf-call-iptables=1`
  - `net.bridge.bridge-nf-call-ip6tables=1`
  - `net.ipv4.ip_forward=1`

Role: `containerd`

- Install containerd.
- Generate `/etc/containerd/config.toml`.
- Set `SystemdCgroup = true`.
- Restart and enable containerd.

Role: `kubernetes`

- Install Kubernetes packages:
  - `kubelet`
  - `kubeadm`
  - `kubectl`
- Pin/hold package versions.
- Enable kubelet.

Role: `kube_vip`

- Pull kube-vip image.
- Generate kube-vip static pod manifest.
- VIP: `<K8S_VIP>`.
- Interface: expected `eth0` inside Ubuntu VM.
- Mode: ARP for flat LAN.

Role: `control_plane`

- Run `kubeadm init` on `k8s-cp-1`.
- Use:

```bash
kubeadm init \
  --control-plane-endpoint "<K8S_VIP>:6443" \
  --upload-certs \
  --pod-network-cidr "<cni-cidr>"
```

- Copy admin kubeconfig.
- Generate join commands.
- Join `k8s-cp-2` and `k8s-cp-3` as control-plane nodes.

Role: `cni`

Recommended CNI for this homelab:

- Cilium if you want modern networking and observability later.
- Calico if you want a classic kubeadm-friendly setup.
- Flannel only if you want the simplest demo.

For a demo cluster, start with Cilium or Calico.

## kube-vip Static Pod Concept

kube-vip runs as a static pod on control-plane nodes.

ARP mode example variables:

```yaml
kube_vip_address: "<K8S_VIP>"
kube_vip_interface: "eth0"
kube_vip_mode: "arp"
kube_vip_controlplane: true
```

The generated manifest should live at:

```text
/etc/kubernetes/manifests/kube-vip.yaml
```

During bootstrap, kube-vip must exist early enough that subsequent control-plane joins can reach the stable endpoint.

## Scheduling Workloads On 3 Masters

For a demo-only cluster, you can allow workloads on control-plane nodes:

```bash
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

For a more production-like cluster, keep the taint and add worker nodes later.

Recommendation:

- Demo mode: allow scheduling on masters.
- Long-term homelab: add 1-3 worker VMs and keep control-plane nodes reserved.

## Verification

After provisioning:

```bash
kubectl get nodes -o wide
kubectl get pods -A
kubectl cluster-info
kubectl get --raw='/readyz?verbose'
```

Expected:

- 3 nodes `Ready`.
- All 3 nodes have control-plane role.
- kube-vip pod running.
- CNI pods running.
- CoreDNS running.

HA checks:

```bash
ping <K8S_VIP>
curl -k https://<K8S_VIP>:6443/readyz
```

Failure test:

1. Reboot the node currently holding VIP.
2. Confirm `<K8S_VIP>` moves to another control-plane node.
3. Confirm `kubectl get nodes` still works.

## Future Ingress: Caddy To Kubernetes

The current homelab ingress boundary is Caddy on the Raspberry Pi 5. Future Kubernetes workloads should integrate with that existing edge instead of exposing random NodePorts directly.

Recommended future model:

```text
Internet / LAN client
  -> VPS / Rathole tunnel
  -> Pi 5 Caddy
  -> Kubernetes ingress endpoint
  -> Kubernetes Service
  -> Pods
```

Internal LAN model:

```text
client -> AdGuard split-horizon DNS -> Pi 5 Caddy -> K8s ingress/service
```

Recommended K8s ingress options:

1. **Ingress controller inside K8s**
   - Install ingress-nginx, Traefik, or Cilium Gateway API.
   - Expose the ingress controller on a stable LAN IP/port.
   - Caddy reverse-proxies selected subdomains to that ingress endpoint.

2. **MetalLB or kube-vip LoadBalancer mode**
   - Allocate a small service IP pool from reserved LAN space.
   - Example future pool: `<K8S_INGRESS_POOL_START>-<K8S_INGRESS_POOL_END>`.
   - Reserve/exclude this pool from MikroTik DHCP first.
   - Caddy routes to the ingress service IP.

3. **NodePort fallback**
   - Caddy routes to `k8s-cp-N:NodePort`.
   - This is acceptable for early tests but is not the preferred long-term model.

Example future Caddy route:

```caddyfile
app-k8s.dungxbuif.com {
    tls {
        dns cloudflare {$CF_API_TOKEN}
        resolvers 1.1.1.1
    }

    reverse_proxy <K8S_INGRESS_POOL_START>:80
}
```

Network planning:

- `<K8S_VIP>`: kube-vip API VIP.
- `<K8S_CP1_IP>-33`: control-plane nodes.
- `<K8S_INGRESS_POOL_START>-49`: recommended future pool for Kubernetes ingress or LoadBalancer services.
- All of these addresses should be reserved or excluded from MikroTik DHCP.

Security guidance:

- Keep Caddy as the TLS and public ingress boundary unless there is a strong reason to move TLS into K8s.
- Do not expose K8s API publicly.
- Do not expose arbitrary NodePorts from MikroTik WAN.
- Route public apps through Caddy and the existing Rathole/VPS path.

## Future Resilience And Load Testing

The cluster should be tested periodically by deliberately stressing and disrupting it in controlled windows. The goal is to verify that kube-vip failover, stacked etcd, CNI, DNS, and ingress routing behave as expected.

Recommended tools:

- `kubectl drain` / `kubectl cordon` for graceful node evacuation.
- Proxmox reboot/shutdown of one VM for hard failover tests.
- `stress-ng` for CPU/memory pressure inside selected nodes.
- `iperf3` for network throughput tests.
- `hey`, `wrk`, or `k6` for HTTP application load.
- `kubectl scale` and rolling restarts for workload churn.
- Optional later: LitmusChaos or Chaos Mesh for Kubernetes-native chaos experiments.

Safe test scenarios:

1. **API VIP failover**
   - Identify which node owns `<K8S_VIP>`.
   - Reboot that VM.
   - Confirm VIP moves and `kubectl get nodes` still works.

2. **Control-plane drain**
   - `kubectl drain k8s-cp-2 --ignore-daemonsets --delete-emptydir-data`
   - Confirm workloads reschedule if control-plane scheduling is enabled.
   - `kubectl uncordon k8s-cp-2`

3. **Ingress load**
   - Deploy a sample HTTP app.
   - Route it through Caddy -> K8s ingress.
   - Run `hey` or `k6` from a LAN client.
   - Watch latency, pod restarts, Caddy logs, node CPU/RAM.

4. **Node pressure**
   - Run controlled `stress-ng` on one node.
   - Confirm alerts fire and workloads remain healthy.

5. **Network path check**
   - Run periodic `iperf3` between Mac/Pi/K8s node.
   - Compare to the current baseline of near-line-rate Gigabit on Mac -> Pi.

Rules for chaos/load tests:

- Run only during an explicit maintenance window.
- Keep a rollback path: Proxmox console, SSH, and known-good kubeconfig.
- Start with one failure mode at a time.
- Record results in this repo after each test.
- Wire Telegram alerts before running destructive tests.

## Operational Notes

Keep these separate:

- Terraform manages VM lifecycle.
- Ansible manages OS and Kubernetes.
- Kubernetes manages cluster workloads.

Avoid manual changes in Proxmox after Terraform owns the VMs, unless the change is later reflected in Terraform.

## Security Notes

- Do not commit Proxmox API tokens.
- Do not commit kubeadm cert keys or kubeconfig with admin credentials.
- Use a dedicated Proxmox API token with limited scope if possible.
- Keep Terraform state out of public repos; it may contain sensitive data.
- Prefer a dedicated SSH key for IaC-created nodes.

## Current Gaps

The current repo still needs:

- `terraform.tfvars.example`.
- Terraform outputs for generated node IPs.
- Ansible inventory generation.
- Ansible roles.
- kube-vip manifest generation.
- CNI install task.
- Verification playbook.
- Cleanup/destroy runbook.
- Caddy-to-K8s ingress implementation.
- Scheduled resilience/load test playbook.

## Minimal Milestone Plan

Milestone 1: VM automation

- Make template script configurable.
- Clean Terraform variables.
- Add outputs.
- Confirm 3 VMs boot and accept SSH.

Milestone 2: OS bootstrap

- Add Ansible inventory.
- Add common/containerd/kubernetes roles.
- Confirm all nodes are kubeadm-ready.

Milestone 3: First control-plane

- Install kube-vip manifest.
- Run kubeadm init on `k8s-cp-1`.
- Install CNI.

Milestone 4: HA control-plane

- Join `k8s-cp-2` and `k8s-cp-3`.
- Verify stacked etcd health.
- Verify kube-vip failover.

Milestone 5: Demo readiness

- Allow scheduling on control-plane nodes if desired.
- Deploy a sample app.
- Add monitoring checks.
- Document recovery and destroy steps.

Milestone 6: Homelab ingress integration

- Reserve a K8s service/ingress IP pool.
- Deploy ingress controller or LoadBalancer implementation.
- Add Caddy route from Pi to K8s ingress.
- Verify public path through VPS/Rathole -> Caddy -> K8s app.

Milestone 7: Resilience testing

- Add a documented chaos/load test playbook.
- Add Telegram monitoring alerts.
- Run kube-vip failover test.
- Run ingress load test.
- Record baseline and regressions.
