# Self-Hosted n8n on Kubernetes with Queue Mode and KEDA Autoscaling

This directory contains Kubernetes manifests to deploy a scalable, self-hosted n8n instance using its **Queue Mode** architecture, with worker autoscaling managed by **KEDA** based on Redis queue length.

## Architecture Overview

This setup utilizes n8n's queue mode for enhanced scalability and reliability:

1.  **Main Process (`n8n-main` Deployment):** Handles UI/API, non-webhook triggers (Cron, Schedule), and manual executions. Runs as a single replica. Configured resources: Requests (CPU: 250m, Mem: 512Mi), Limits (CPU: 1000m, Mem: 1Gi).
2.  **Worker Process (`n8n-worker` Deployment):** Executes workflows pulled from the Redis queue. Autoscaled by KEDA based on queue length. Configured resources: Requests (CPU: 300m, Mem: 512Mi), Limits (CPU: 1500m, Mem: 1.5Gi).
3.  **Webhook Process (`n8n-webhook` Deployment):** (Optional but included) Dedicated process to handle incoming production webhooks, placing jobs onto the Redis queue. Configured resources: Requests (CPU: 100m, Mem: 256Mi), Limits (CPU: 500m, Mem: 512Mi).
4.  **PostgreSQL (`postgres` Deployment):** Stores persistent n8n data (workflows, credentials, execution logs). Uses `postgres:11` (as per `postgres-deployment.yaml`; `postgres:13` or later is generally recommended for optimal performance). Configured resources: Requests (CPU: 500m, Mem: 1Gi), Limits (CPU: 2, Mem: 2Gi). Includes an init script (`postgres-configmap.yaml`) to create a non-root user specified in `postgres-secret.yaml`.
5.  **Redis (`redis` Deployment):** Acts as the message broker (job queue) between main/webhook processes and workers. Configured resources: Requests (CPU: 100m, Mem: 128Mi), Limits (CPU: 500m, Mem: 256Mi).
6.  **KEDA (`keda-scaledobject`, `keda-trigger-auth`):** Monitors the Redis job queue (`bull:default:wait` list) and automatically scales the `n8n-worker` deployment replicas based on the number of pending jobs.

## Prerequisites

*   A running Kubernetes cluster.
*   `kubectl` configured to interact with your cluster.
*   Persistent storage provider configured (e.g., `longhorn`, specified in PVCs).
*   Ingress controller installed (e.g., `traefik`, specified in `n8n-ingress.yaml`).
*   **KEDA installed in your cluster.** Follow the official KEDA installation guide: [https://keda.sh/docs/latest/deploy/](https://keda.sh/docs/latest/deploy/)

## Deployment Steps

1.  **Review Secrets:**
    *   Update placeholder values (`changeUser`, `changePassword`) in `postgres-secret.yaml` for keys: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_NON_ROOT_USER`, `POSTGRES_NON_ROOT_PASSWORD`.
    *   Update placeholder value (`changeRedisPassword`) in `redis-secret.yaml` for key: `REDIS_PASSWORD`.
    *   Review/change the `N8N_ENCRYPTION_KEY` in `n8n-encryption-secret.yaml`. **This key is critical for credential encryption - back it up securely!**
2.  **Apply Namespace:**
    ```bash
    kubectl apply -f namespace.yaml
    ```
3.  **Apply Secrets and ConfigMaps:**
    ```bash
    kubectl apply -f postgres-secret.yaml
    kubectl apply -f redis-secret.yaml
    kubectl apply -f n8n-encryption-secret.yaml
    kubectl apply -f postgres-configmap.yaml # Provides init script for Postgres user creation
    ```
4.  **Apply PersistentVolumeClaims:**
    ```bash
    kubectl apply -f postgres-claim0-persistentvolumeclaim.yaml # PVC named postgresql-pv (1Gi, longhorn)
    kubectl apply -f n8n-claim0-persistentvolumeclaim.yaml # PVC named n8n-claim0 (1Gi, longhorn)
    ```
5.  **Deploy Dependencies (Postgres & Redis):**
    ```bash
    kubectl apply -f postgres-deployment.yaml
    kubectl apply -f postgres-service.yaml # Headless service for Postgres
    kubectl apply -f redis-deployment.yaml
    kubectl apply -f redis-service.yaml
    ```
    Wait for Postgres and Redis pods to be running and ready.
6.  **Deploy n8n Components:**
    ```bash
    kubectl apply -f n8n-deployment.yaml # Main process
    kubectl apply -f n8n-service.yaml # Service for main process
    kubectl apply -f n8n-worker-deployment.yaml # Worker process
    kubectl apply -f n8n-webhook-deployment.yaml # Optional webhook process
    kubectl apply -f n8n-webhook-service.yaml # Service for webhook process
    ```
7.  **Configure KEDA Autoscaling:**
    ```bash
    kubectl apply -f keda-trigger-auth.yaml # Allows KEDA to read redis-secret
    kubectl apply -f keda-scaledobject.yaml # Defines scaling rules for n8n-worker
    ```
8.  **Configure Ingress:**
    *   Ensure the `host` in `n8n-ingress.yaml` (`n8n.dungxbuif.com`) points to your cluster's ingress IP/DNS.
    *   Ensure `ingressClassName` matches your ingress controller (`traefik`).
    *   Review TLS annotations if using HTTPS (recommended).
    ```bash
    kubectl apply -f n8n-ingress.yaml
    ```

## Configuration Highlights

*   **Execution Mode:** `EXECUTIONS_MODE=queue` is set in all n8n deployments.
*   **Database & Redis:** Connection details are configured via environment variables, sourcing secrets where necessary. Postgres uses the non-root user created by the init script.
*   **Webhook URL:** `WEBHOOK_URL` in `n8n-deployment.yaml` must be set to the public-facing URL for n8n (e.g., `https://n8n.dungxbuif.com`).
*   **Webhook Handling:** `N8N_DISABLE_PRODUCTION_MAIN_PROCESS=true` in `n8n-deployment.yaml` ensures production webhooks (`/webhook/`) are handled only by the dedicated `n8n-webhook` process. Test webhooks (`/webhook-test/`) are still routed to the main process via the Ingress.
*   **Worker Concurrency:** Set via `--concurrency` arg in `n8n-worker-deployment.yaml` (current: 10). Tune based on workflow type and pod resources.
*   **KEDA Scaling:** The `listLength` parameter in `keda-scaledobject.yaml` (current: 5) defines the target number of pending jobs per worker replica. Lowering this value makes scaling more aggressive. `minReplicaCount` (1) and `maxReplicaCount` (5) define the scaling boundaries.
*   **Data Pruning:** Execution data pruning is enabled in `n8n-deployment.yaml` to manage database size (`EXECUTIONS_DATA_PRUNE=true`, `EXECUTIONS_DATA_MAX_AGE=336`, `EXECUTIONS_DATA_SAVE_ON_SUCCESS=none`).
*   **DB Pool Size:** Increased to 8 for main and worker deployments (`DB_POSTGRESDB_POOL_SIZE=8`).

## Scaling

*   **Workers:** Automatically scaled by KEDA based on the `bull:default:wait` Redis list length. Adjust `minReplicaCount`, `maxReplicaCount`, and `listLength` in `keda-scaledobject.yaml` as needed.
*   **Webhook Process:** Manually scale the `n8n-webhook` deployment (`kubectl scale deployment n8n-webhook --replicas=X -n n8n`) if webhook ingestion becomes a bottleneck. Alternatively, configure a standard HPA based on CPU/Memory for the webhook deployment.
*   **Main Process:** Typically runs as a single replica. Scaling it requires an Enterprise license and specific HA configuration (`N8N_MULTI_MAIN_SETUP_ENABLED`).
*   **Dependencies:** Scale PostgreSQL and Redis resources (CPU/Memory in Deployments) or replicas if they become bottlenecks. Consider upgrading Postgres image (`postgres:11` -> `postgres:13+`).
*   **Resources:** Adjust CPU/Memory requests and limits in the Deployment YAMLs based on observed usage via monitoring.

## Monitoring

*   **KEDA:** Check KEDA logs and the status of the `ScaledObject` (`kubectl get scaledobject n8n-worker-redis-scaler -n n8n -o yaml`).
*   **Worker Replicas:** Monitor the number of `n8n-worker` pods (`kubectl get pods -n n8n -l app=n8n-worker`).
*   **Redis Queue:** Monitor the length of the `bull:default:wait` list in Redis (e.g., using `redis-cli LLEN bull:default:wait`).
*   **Pod Resources:** Monitor CPU and Memory usage of all pods (main, worker, webhook, postgres, redis) using `kubectl top pods -n n8n` or a monitoring stack like Prometheus/Grafana.
*   **n8n Metrics:** Check the `/metrics` endpoint on n8n pods for internal metrics like event loop lag.

## Uninstallation

```bash
kubectl delete -f n8n-ingress.yaml -n n8n
kubectl delete -f keda-scaledobject.yaml -n n8n
kubectl delete -f keda-trigger-auth.yaml -n n8n
kubectl delete -f n8n-webhook-service.yaml -n n8n
kubectl delete -f n8n-webhook-deployment.yaml -n n8n
kubectl delete -f n8n-worker-deployment.yaml -n n8n
kubectl delete -f n8n-service.yaml -n n8n
kubectl delete -f n8n-deployment.yaml -n n8n
kubectl delete -f redis-service.yaml -n n8n
kubectl delete -f redis-deployment.yaml -n n8n
kubectl delete -f postgres-service.yaml -n n8n
kubectl delete -f postgres-deployment.yaml -n n8n
kubectl delete -f postgres-configmap.yaml -n n8n
kubectl delete -f n8n-encryption-secret.yaml -n n8n
kubectl delete -f redis-secret.yaml -n n8n
kubectl delete -f postgres-secret.yaml -n n8n
# Warning: The following commands delete persistent data!
kubectl delete -f n8n-claim0-persistentvolumeclaim.yaml -n n8n
kubectl delete -f postgres-claim0-persistentvolumeclaim.yaml -n n8n
# End Warning
kubectl delete -f namespace.yaml
```

