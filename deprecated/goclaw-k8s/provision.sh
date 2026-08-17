#!/bin/bash
# IaC Provisioning Script for GoClaw on Homelab Kubernetes Cluster
# This script handles database user setup instructions, secret generation,
# and applying the Kubernetes manifests.
#
# Usage:
#   ./provision.sh           # Dry-run mode: prints commands and instructions
#   ./provision.sh --execute # Execution mode: runs the provisioning steps

set -euo pipefail

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

EXECUTE=false
if [[ "${1:-}" == "--execute" ]]; then
  EXECUTE=true
fi

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# 1. Generate secure random tokens
log_info "Generating secure random tokens..."
GATEWAY_TOKEN=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -hex 16)

DB_USER="goclaw_user"
DB_NAME="goclaw"
DB_HOST="10.10.0.5"
DB_PORT="5432"
DB_URL="postgres://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?sslmode=disable"

# Determine path of the manifests
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$EXECUTE" = false ]; then
  log_warn "--- DRY-RUN MODE: NO ACTIONS WILL BE DEPLOYED ---"
  echo ""
  log_step "1. Database Isolation (Execute on Raspberry Pi 5 / Controller):"
  echo "Run the following SQL commands inside the postgres container on Pi 5:"
  echo -e "${YELLOW}ssh 10.10.0.5 \"docker exec -i postgres psql -U admin -d homelab -c \\\"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}'; ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER}; GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};\\\"\"${NC}"
  echo ""
  log_step "2. Kubernetes Secrets & Namespace Creation:"
  echo "Run these commands on your cluster-admin context to create the namespace and store generated credentials:"
  echo -e "${YELLOW}kubectl create namespace goclaw || true${NC}"
  echo -e "${YELLOW}kubectl create secret generic goclaw-secrets \\"
  echo "  --namespace=goclaw \\"
  echo "  --from-literal=gateway-token=\"${GATEWAY_TOKEN}\" \\"
  echo "  --from-literal=encryption-key=\"${ENCRYPTION_KEY}\" \\"
  echo -e "  --from-literal=database-url=\"${DB_URL}\"${NC}"
  echo ""
  log_step "3. Kubernetes Manifests Deployment:"
  echo "Apply the IaC manifests in the following order:"
  echo -e "${YELLOW}kubectl apply -f ${SCRIPT_DIR}/ns.yaml${NC}"
  echo -e "${YELLOW}kubectl apply -f ${SCRIPT_DIR}/pvc.yaml${NC}"
  echo -e "${YELLOW}kubectl apply -f ${SCRIPT_DIR}/service.yaml${NC}"
  echo -e "${YELLOW}kubectl apply -f ${SCRIPT_DIR}/ingressroute.yaml${NC}"
  echo -e "${YELLOW}kubectl apply -f ${SCRIPT_DIR}/deployment.yaml${NC}"
  echo ""
  log_step "4. Pi 5 Gateway Configuration:"
  echo "Add the routing handle to /ssd-data/infra/Caddyfile on Pi 5 and reload Caddy:"
  echo -e "${YELLOW}    @goclaw host goclaw.dungxbuif.com"
  echo "    handle @goclaw {"
  echo "        reverse_proxy 10.10.0.30:80"
  echo -e "    }${NC}"
  echo ""
  echo "Add DNS rewrite rule in AdGuard Home:"
  echo -e "${YELLOW}goclaw.dungxbuif.com -> 10.10.0.5${NC}"
  echo ""
  log_info "To actually run these commands, execute this script with the --execute flag: ./provision.sh --execute"
  exit 0
fi

# Actual execution
log_info "--- STARTING EXECUTION MODE ---"

# Step 1: Create DB User
log_step "Step 1: Creating database user '${DB_USER}' and granting privileges..."
ssh 10.10.0.5 "docker exec -i postgres psql -U admin -d homelab -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}'; ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER}; GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};\""
log_info "Database user '${DB_USER}' configured."

# Step 2: K8s Namespace & Secrets
log_step "Step 2: Provisioning namespace and secrets in Kubernetes..."
kubectl apply -f "${SCRIPT_DIR}/ns.yaml"
kubectl delete secret goclaw-secrets --namespace=goclaw --ignore-not-found=true
kubectl create secret generic goclaw-secrets \
  --namespace=goclaw \
  --from-literal=gateway-token="${GATEWAY_TOKEN}" \
  --from-literal=encryption-key="${ENCRYPTION_KEY}" \
  --from-literal=database-url="${DB_URL}"
log_info "Kubernetes secrets created successfully."

# Step 3: Apply manifests
log_step "Step 3: Deploying Kubernetes resources..."
kubectl apply -f "${SCRIPT_DIR}/pvc.yaml"
kubectl apply -f "${SCRIPT_DIR}/service.yaml"
kubectl apply -f "${SCRIPT_DIR}/ingressroute.yaml"
kubectl apply -f "${SCRIPT_DIR}/deployment.yaml"
log_info "Manifests applied successfully."

log_info "--- DEPLOYMENT INITIAL STAGE COMPLETE ---"
log_warn "Next actions required on Raspberry Pi 5:"
log_warn "1. Update /ssd-data/infra/Caddyfile with the goclaw proxy handler."
log_warn "2. Reload Caddy: ssh 10.10.0.5 'cd /ssd-data/infra && docker compose exec -w /etc/caddy caddy caddy reload'"
log_warn "3. Add DNS rewrite in AdGuard Home for goclaw.dungxbuif.com -> 10.10.0.5"
