---
type: Reference
title: "Code Index: webhook-relay"
description: "Aggregated code index for webhook-relay folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: webhook-relay

> This index aggregates code files in the [[webhook-relay/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [database.yml](./database.yml)

```yaml
# PostgreSQL configuration
---
apiVersion: v1
kind: Secret
metadata:
  namespace: webhookrelay
  name: postgres-secret
type: Opaque
stringData:
  POSTGRES_USER: webhookrelay
  POSTGRES_PASSWORD: <DEPRECATED_WEBHOOK_RELAY_POSTGRES_PASSWORD>
  POSTGRES_DB: webhookrelay
  POSTGRES_NON_ROOT_USER: webhookrelay
  POSTGRES_NON_ROOT_PASSWORD: <DEPRECATED_WEBHOOK_RELAY_POSTGRES_PASSWORD>
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: init-data
  namespace: webhookrelay
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
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
  namespace: webhookrelay
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 512Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: webhookrelay
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:16.1
          env:
          - name: PGDATA
            value: /var/lib/postgresql/data/pgdata
          - name: POSTGRES_DB
            valueFrom:
              secretKeyRef:
                key: POSTGRES_DB
                name: postgres-secret
          - name: POSTGRES_PASSWORD
            valueFrom:
              secretKeyRef:
                key: POSTGRES_PASSWORD
                name: postgres-secret
          - name: POSTGRES_USER
            valueFrom:
              secretKeyRef:
                key: POSTGRES_USER
                name: postgres-secret
          - name: POSTGRES_NON_ROOT_USER
            valueFrom:
              secretKeyRef:
                key: POSTGRES_NON_ROOT_USER
                name: postgres-secret
          - name: POSTGRES_NON_ROOT_PASSWORD
            valueFrom:
              secretKeyRef:
                key: POSTGRES_NON_ROOT_PASSWORD
                name: postgres-secret
          ports:
            - containerPort: 5432
          resources:
            limits:
              cpu: 200m
              memory: 256Mi
            requests:
              cpu: 100m
              memory: 128Mi
          volumeMounts:
            - mountPath: /var/lib/postgresql/data
              name: postgres-data
            - mountPath: /docker-entrypoint-initdb.d
              name: init-script
      volumes:
        - name: postgres-data
          persistentVolumeClaim:
            claimName: postgres-data
        - name: init-script
          configMap:
            name: init-data
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: webhookrelay
spec:
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
  selector:
    app: postgres

# Redis configuration
---
apiVersion: v1
kind: Secret
metadata:
  namespace: webhookrelay
  name: redis-secret
type: Opaque
stringData:
  REDIS_PASSWORD: "<DEPRECATED_WEBHOOK_RELAY_REDIS_PASSWORD>"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-data
  namespace: webhookrelay
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn
  resources:
    requests:
      storage: 512Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: webhookrelay
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7.2.4
          args:
            - --requirepass
            - $(REDIS_PASSWORD)
          env:
          - name: REDIS_PASSWORD
            valueFrom:
              secretKeyRef:
                name: redis-secret
                key: REDIS_PASSWORD
          ports:
            - containerPort: 6379
          resources:
            limits:
              cpu: 100m
              memory: 128Mi
            requests:
              cpu: 50m
              memory: 64Mi
          volumeMounts:
            - mountPath: /data
              name: redis-data
      volumes:
        - name: redis-data
          persistentVolumeClaim:
            claimName: redis-data
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: webhookrelay
spec:
  ports:
    - port: 6379
      targetPort: 6379
  selector:
    app: redis
```

---

## [deployment.yml](./deployment.yml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: transponder
  namespace: webhookrelay
spec:
  replicas: 1
  selector:
    matchLabels:
      app: transponder
  template:
    metadata:
      labels:
        app: transponder
    spec:
      containers:
        - name: transponder
          image: webhookrelay/transponder:latest
          imagePullPolicy: Always
          command: [
            "/bin/transponder", 
            "--status-server",
            "--api-server"]
          envFrom:
            - configMapRef:
                name: webhookrelay-config
            - secretRef:
                name: webhookrelay-secrets
          ports:
            - containerPort: 9300 # API/Dashboard HTTPS port
            - containerPort: 9301 # HTTP port 
            - containerPort: 9302 # GRPC port
          livenessProbe:
            httpGet:
              path: /health
              port: 9301
            initialDelaySeconds: 30
            timeoutSeconds: 10
            periodSeconds: 3
          resources:
            limits:
              cpu: 400m
              memory: 500Mi
            requests:
              cpu: 100m
              memory: 128Mi
```

---

## [hpa.yml](./hpa.yml)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webhookrelay-hpa
  namespace: webhookrelay
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: transponder
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

---

## [ingress.yml](./ingress.yml)

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: webhookrelay-ingressroute
  namespace: webhookrelay
spec:
  entryPoints:
    - websecure
  routes:
    - kind: Rule
      match: Host(`webhookrelay.dungxbuif.com`)
      services:
        - name: webhookrelay-service
          port: 80
    - kind: Rule
      match: Host(`webhookrelay.dungxbuif.com`) && PathPrefix(`/api/v1/grpc`)
      services:
        - name: webhookrelay-service
          port: 9302
          scheme: h2c
```

---

## [namespace.yml](./namespace.yml)

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: webhookrelay

```

---

## [service.yml](./service.yml)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: webhookrelay-service
  namespace: webhookrelay
spec:
  selector:
    app: transponder
  ports:
    - name: api-https
      port: 443
      targetPort: 9300
      protocol: TCP
    - name: api-http
      port: 80
      targetPort: 9301
      protocol: TCP
    - name: grpc
      port: 9302
      targetPort: 9302
      protocol: TCP
  type: ClusterIP
```

---

## [webhook-relay-configmap.yml](./webhook-relay-configmap.yml)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: webhookrelay-config
  namespace: webhookrelay
data:
  # General configuration
  LOGS_RETENTION_DAYS: "30"
  LOGS_RETENTION_JOB_SCHEDULE: "@midnight"

```

---

## [webhookrelay-secrets.yml](./webhookrelay-secrets.yml)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: webhookrelay-secrets
  namespace: webhookrelay
type: Opaque
stringData:
  # Admin credentials
  ADMIN_USERNAME: "admin"
  ADMIN_PASSWORD: "<DEPRECATED_WEBHOOK_RELAY_ADMIN_PASSWORD>"
  
  # JWT authentication
  JWT_SECRET: "<DEPRECATED_WEBHOOK_RELAY_JWT_SECRET>"
  
  # License information
  LICENSE: "your-license-key"
  
  # Database configuration - updated to use the postgres service
  POSTGRES_HOST: "postgres.webhookrelay.svc.cluster.local"
  POSTGRES_USER: "webhookrelay"
  POSTGRES_PASSWORD: "<DEPRECATED_WEBHOOK_RELAY_POSTGRES_PASSWORD>"
  POSTGRES_DB: "webhookrelay"
  
  # Redis configuration - updated to use redis service with password
  REDIS_HOST: "redis.webhookrelay.svc.cluster.local:6379"
  REDIS_PASSWORD: "<DEPRECATED_WEBHOOK_RELAY_REDIS_PASSWORD>"
```

---
