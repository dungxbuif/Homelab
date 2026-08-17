---
type: Reference
title: "Code Index: n8n"
description: "Aggregated code index for n8n folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: n8n

> This index aggregates code files in the [[n8n/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [keda-scaledobject.yaml](./keda-scaledobject.yaml)

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: n8n-worker-redis-scaler
  namespace: n8n
spec:
  scaleTargetRef:
    name: n8n-worker # Name of the Deployment to scale
  pollingInterval: 15  # Check queue length every 15 seconds
  cooldownPeriod:  300 # Wait 5 minutes after last activity before scaling down
  minReplicaCount: 1   # Minimum number of workers (set to 0 for scale-to-zero if desired)
  maxReplicaCount: 5  # Maximum number of workers (adjust as needed)
  triggers:
  - type: redis
    metadata:
      # Required: Redis server address (host:port)
      address: redis-service.n8n.svc.cluster.local:6379
      # Required: Name of the BullMQ waiting list
      listName: bull:default:wait # Verify this key name in your Redis instance if using custom queue names
      # Required: Target average queue length per worker replica. Tune this value.
      # Lower value = more aggressive scaling up.
      listLength: "5"
      # Optional: Activation threshold for scaling from 0 (if minReplicaCount=0)
      # activationListLength: "1"
    authenticationRef: # Reference the TriggerAuthentication for Redis credentials
      name: keda-redis-secrets

```

---

## [keda-trigger-auth.yaml](./keda-trigger-auth.yaml)

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-redis-secrets
  namespace: n8n
spec:
  secretTargetRef:
    - parameter: password # Corresponds to the 'password' field needed by the Redis scaler
      name: redis-secret # Name of the K8s secret containing Redis credentials
      key: REDIS_PASSWORD # Key within the secret holding the password

```

---

## [n8n-claim0-persistentvolumeclaim.yaml](./n8n-claim0-persistentvolumeclaim.yaml)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  labels:
    service: n8n-claim0
  name: n8n-claim0
  namespace: n8n
spec:
  storageClassName: longhorn
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi

```

---

## [n8n-deployment.yaml](./n8n-deployment.yaml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: n8n-main
  name: n8n-main
  namespace: n8n
spec:
  replicas: 1
  selector:
    matchLabels:
      app: n8n-main
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: n8n-main
    spec:
      containers:
        - env:
            - name: EXECUTIONS_MODE
              value: queue
            - name: QUEUE_BULL_REDIS_HOST
              value: redis-service.n8n.svc.cluster.local
            - name: QUEUE_BULL_REDIS_PORT
              value: "6379"
            - name: QUEUE_BULL_REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: redis-secret
                  key: REDIS_PASSWORD
            - name: WEBHOOK_URL
              value: https://n8n.dungxbuif.com
            - name: DB_TYPE
              value: postgresdb
            - name: DB_POSTGRESDB_HOST
              value: postgres-service.n8n.svc.cluster.local
            - name: DB_POSTGRESDB_PORT
              value: "5432"
            - name: DB_POSTGRESDB_DATABASE
              value: n8n
            - name: DB_POSTGRESDB_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_NON_ROOT_USER
            - name: DB_POSTGRESDB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_NON_ROOT_PASSWORD
            - name: N8N_PROTOCOL
              value: https
            - name: N8N_HOST
              value: "0.0.0.0"
            - name: N8N_PORT
              value: "5678"
            - name: N8N_ENCRYPTION_KEY
              valueFrom:
                secretKeyRef:
                  name: n8n-encryption-secret
                  key: N8N_ENCRYPTION_KEY
            - name: N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS
              value: "true"
          image: n8nio/n8n
          name: n8n-main
          ports:
            - containerPort: 5678
          readinessProbe:
            httpGet:
              path: /healthz
              port: 5678
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /healthz
              port: 5678
            initialDelaySeconds: 60
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 5
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          volumeMounts:
            - mountPath: /home/node/.n8n
              name: n8n-claim0
      restartPolicy: Always
      volumes:
        - name: n8n-claim0
          persistentVolumeClaim:
            claimName: n8n-claim0

```

---

## [n8n-encryption-secret.yaml](./n8n-encryption-secret.yaml)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: n8n-encryption-secret
  namespace: n8n
type: Opaque
stringData:
  N8N_ENCRYPTION_KEY: "6bbb07de1c192274755eede1fbbc21df722c5f67a3174371f15d9f55662afb02"
```

---

## [n8n-ingress.yaml](./n8n-ingress.yaml)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: n8n-ingress
  namespace: n8n
  
spec:
  ingressClassName: traefik
  rules:
  - host: n8n.dungxbuif.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: n8n-main-service
            port:
              number: 5678
      - path: /webhook-test/
        pathType: Prefix
        backend:
          service:
            name: n8n-main-service
            port:
              number: 5678
```

---

## [n8n-service.yaml](./n8n-service.yaml)

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    app: n8n-main
  name: n8n-main-service
  namespace: n8n
spec:
  type: ClusterIP
  ports:
    - name: "5678"
      port: 5678
      targetPort: 5678
      protocol: TCP
  selector:
    app: n8n-main

```

---

## [n8n-webhook-deployment.yaml](./n8n-webhook-deployment.yaml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: n8n-webhook
  namespace: n8n
  labels:
    app: n8n-webhook
spec:
  replicas: 1 # Start with 1, can be scaled manually or with HPA if needed
  selector:
    matchLabels:
      app: n8n-webhook
  template:
    metadata:
      labels:
        app: n8n-webhook
    spec:
      containers:
      - name: n8n-webhook
        image: n8nio/n8n
        command: ["n8n", "webhook"]
        env:
        - name: EXECUTIONS_MODE
          value: queue
        - name: QUEUE_BULL_REDIS_HOST
          value: redis-service.n8n.svc.cluster.local
        - name: QUEUE_BULL_REDIS_PORT
          value: "6379"
        - name: QUEUE_BULL_REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: REDIS_PASSWORD
        - name: DB_TYPE
          value: postgresdb
        - name: DB_POSTGRESDB_HOST
          value: postgres-service.n8n.svc.cluster.local
        - name: DB_POSTGRESDB_PORT
          value: "5432"
        - name: DB_POSTGRESDB_DATABASE
          value: n8n
        - name: DB_POSTGRESDB_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_NON_ROOT_USER
        - name: DB_POSTGRESDB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_NON_ROOT_PASSWORD
        - name: N8N_ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: n8n-encryption-secret
              key: N8N_ENCRYPTION_KEY
        - name: N8N_PORT # Webhook process also listens on a port
          value: "5678"
        resources: # Define resources for webhook pods (typically less than workers)
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        ports:
        - containerPort: 5678
        readinessProbe: # Add probes for webhook process
          httpGet:
            path: /healthz
            port: 5678
          initialDelaySeconds: 15
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: 5678
          initialDelaySeconds: 30
          periodSeconds: 30
      restartPolicy: Always

```

---

## [n8n-webhook-service.yaml](./n8n-webhook-service.yaml)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: n8n-webhook-service
  namespace: n8n
  labels:
    app: n8n-webhook
spec:
  type: ClusterIP
  ports:
  - name: "5678"
    port: 5678
    targetPort: 5678
    protocol: TCP
  selector:
    app: n8n-webhook

```

---

## [n8n-worker-deployment.yaml](./n8n-worker-deployment.yaml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: n8n-worker
  namespace: n8n
  labels:
    app: n8n-worker
spec:
  replicas: 1 
  selector:
    matchLabels:
      app: n8n-worker
  template:
    metadata:
      labels:
        app: n8n-worker
    spec:
      containers:
      - name: n8n-worker
        image: n8nio/n8n
        command: ["n8n", "worker"]
        args: ["--concurrency=10"]
        env:
        - name: EXECUTIONS_MODE
          value: queue
        - name: QUEUE_BULL_REDIS_HOST
          value: redis-service.n8n.svc.cluster.local
        - name: QUEUE_BULL_REDIS_PORT
          value: "6379"
        - name: QUEUE_BULL_REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: REDIS_PASSWORD
        - name: DB_TYPE
          value: postgresdb
        - name: DB_POSTGRESDB_HOST
          value: postgres-service.n8n.svc.cluster.local
        - name: DB_POSTGRESDB_PORT
          value: "5432"
        - name: DB_POSTGRESDB_DATABASE
          value: n8n
        - name: DB_POSTGRESDB_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_NON_ROOT_USER
        - name: DB_POSTGRESDB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_NON_ROOT_PASSWORD
        - name: N8N_ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: n8n-encryption-secret
              key: N8N_ENCRYPTION_KEY
        # Explicitly set N8N_PORT to avoid conflict with K8s service variables
        - name: N8N_PORT
          value: "5678"
        # Add recommended env vars based on logs
        - name: N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS
          value: "true"
        - name: N8N_RUNNERS_ENABLED
          value: "true"
        - name: OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS
          value: "true"
        # Add other necessary env vars if workflows require them (e.g., NODE_OPTIONS)
        resources: # Define resources for worker pods
          requests:
            memory: "512Mi"
            cpu: "300m"
          limits:
            memory: "1.5Gi" # Allow more memory for execution
            cpu: "1500m" # Allow bursting
        # No volume mounts needed by default for workers unless workflows interact with filesystem
      restartPolicy: Always

```

---

## [namespace.yaml](./namespace.yaml)

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: n8n

```

---

## [postgres-claim0-persistentvolumeclaim.yaml](./postgres-claim0-persistentvolumeclaim.yaml)

```yaml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: postgresql-pv
  namespace: n8n
spec:
  storageClassName: longhorn
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi

```

---

## [postgres-configmap.yaml](./postgres-configmap.yaml)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: init-data
  namespace: n8n
data:
  init-data.sh: |
    #!/bin/bash
    set -e;
    if [ -n "${POSTGRES_NON_ROOT_USER:-}" ] && [ -n "${POSTGRES_NON_ROOT_PASSWORD:-}" ]; then
    	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    		CREATE USER "${POSTGRES_NON_ROOT_USER}" WITH PASSWORD '${POSTGRES_NON_ROOT_PASSWORD}';
    		GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO "${POSTGRES_NON_ROOT_USER}";
    	EOSQL
    else
    	echo "SETUP INFO: No Environment variables given!"
    fi
```

---

## [postgres-deployment.yaml](./postgres-deployment.yaml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    service: postgres-n8n
  name: postgres
  namespace: n8n
spec:
  replicas: 1
  selector:
    matchLabels:
      service: postgres-n8n
  strategy:
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
    type: RollingUpdate
  template:
    metadata:
      labels:
        service: postgres-n8n
    spec:
      containers:
        - image: postgres:11
          name: postgres
          resources:
            limits:
              cpu: "500m"
              memory: 512Mi
            requests:
              cpu: "250m"
              memory: 512Mi
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: postgresql-pv
              mountPath: /var/lib/postgresql/data
            - name: init-data
              mountPath: /docker-entrypoint-initdb.d/init-n8n-user.sh
              subPath: init-data.sh
          env:
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata      
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_PASSWORD
            - name: POSTGRES_DB
              value: n8n
            - name: POSTGRES_NON_ROOT_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_NON_ROOT_USER
            - name: POSTGRES_NON_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_NON_ROOT_PASSWORD
            - name:   POSTGRES_HOST
              value: postgres-service
            - name: POSTGRES_PORT
              value: '5432'
      restartPolicy: Always
      volumes:
        - name: postgresql-pv
          persistentVolumeClaim:
            claimName: postgresql-pv
        - name: postgres-secret
          secret:
            secretName: postgres-secret
        - name: init-data
          configMap:
            name: init-data
            defaultMode: 0744

```

---

## [postgres-secret.yaml](./postgres-secret.yaml)

```yaml
apiVersion: v1
kind: Secret
metadata:
  namespace: n8n
  name: postgres-secret
type: Opaque
stringData:
  POSTGRES_USER: changeUser
  POSTGRES_PASSWORD: changePassword
  POSTGRES_DB: n8n
  POSTGRES_NON_ROOT_USER: changeUser
  POSTGRES_NON_ROOT_PASSWORD: changePassword
```

---

## [postgres-service.yaml](./postgres-service.yaml)

```yaml
apiVersion: v1
kind: Service
metadata:
  labels:
    service: postgres-n8n
  name: postgres-service
  namespace: n8n
spec:
  clusterIP: None
  ports:
    - name: "5432"
      port: 5432
      targetPort: 5432
      protocol: TCP
  selector:
    service: postgres-n8n

```

---

## [redis-deployment.yaml](./redis-deployment.yaml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: n8n
  labels:
    app: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:6-alpine
        command: ["/bin/sh", "-c"]
        args: ["redis-server --requirepass \"${REDIS_PASSWORD}\""]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: REDIS_PASSWORD
        ports:
        - containerPort: 6379
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"

```

---

## [redis-secret.yaml](./redis-secret.yaml)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: redis-secret
  namespace: n8n
type: Opaque
stringData:
    REDIS_PASSWORD: "p8Tr5K2q@Jz7XvN9!Lm3yBs6"

```

---

## [redis-service.yaml](./redis-service.yaml)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: n8n
  labels:
    app: redis
spec:
  ports:
  - port: 6379
    targetPort: 6379
  selector:
    app: redis

```

---
