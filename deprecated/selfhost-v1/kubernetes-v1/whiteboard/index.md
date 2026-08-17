---
type: Reference
title: "Code Index: whiteboard"
description: "Aggregated code index for whiteboard folder"
timestamp: 2026-07-03T15:11:00Z
---

# Code Index: whiteboard

> This index aggregates code files in the [[whiteboard/]] directory.
> Edit the source files directly; this index is auto-generated for Obsidian reading.

---

## [be-deployment.yml](./be-deployment.yml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whiteboard-be
  namespace: whiteboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: whiteboard-be
  template:
    metadata:
      labels:
        app: whiteboard-be
    spec:
      containers:
        - name: whiteboard-be
          image: registry.dungxbuif.com/whiteboard/whiteboard-be:592db6a9b3127af2c4c8bad713e62199e62d9269
          envFrom:
            - configMapRef:
                name: whiteboard-be
          ports:
            - containerPort: 80
      imagePullSecrets:
        - name: regcred

```

---

## [be-job.yml](./be-job.yml)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: whiteboard-db-migration
  namespace: whiteboard
spec:
  backoffLimit: 3
  template:
    spec:
      containers:
        - name: db-migrations
          image: registry.dungxbuif.com/whiteboard/whiteboard-migration:592db6a9b3127af2c4c8bad713e62199e62d9269
          envFrom:
            - configMapRef:
                name: whiteboard-be
      restartPolicy: Never
      imagePullSecrets:
        - name: regcred

```

---

## [dashboard-deployment.yml](./dashboard-deployment.yml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
   name: whiteboard-dashboard
   namespace: whiteboard
spec:
   replicas: 1
   selector:
      matchLabels:
         app: whiteboard-dashboard
   template:
      metadata:
         labels:
            app: whiteboard-dashboard
      spec:
         containers:
            - name: whiteboard-dashboard
              image: registry.dungxbuif.com/whiteboard/whiteboard-dashboard:6c2aa38b9f4707eb3483c8a33a79d0ffa647bdd9
              ports:
                 - containerPort: 3000
         imagePullSecrets:
            - name: regcred

```

---

## [fe-deployment.yml](./fe-deployment.yml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whiteboard-fe
  namespace: whiteboard
spec:
  replicas: 1
  selector:
    matchLabels:
      app: whiteboard-fe
  template:
    metadata:
      labels:
        app: whiteboard-fe
    spec:
      containers:
        - name: whiteboard-fe
          image: registry.dungxbuif.com/whiteboard/whiteboard-fe:8d6fa9e20d912bdc2425ecbd4c89d7e1830b9068
          ports:
            - containerPort: 80
      imagePullSecrets:
        - name: regcred

```

---

## [service.yml](./service.yml)

```yaml
apiVersion: v1
kind: Service
metadata:
   name: whiteboard-be
   namespace: whiteboard
spec:
   selector:
      app: whiteboard-be
   ports:
      - port: 80
        targetPort: 80

---
apiVersion: v1
kind: Service
metadata:
   name: whiteboard-dashboard
   namespace: whiteboard
spec:
   selector:
      app: whiteboard-dashboard
   ports:
      - port: 80
        targetPort: 3000
---
apiVersion: v1
kind: Service
metadata:
   name: whiteboard-fe
   namespace: whiteboard
spec:
   selector:
      app: whiteboard-fe
   ports:
      - port: 80
        targetPort: 80
---
apiVersion: v1
kind: Service
metadata:
   name: whiteboard-ws
   namespace: whiteboard
spec:
   selector:
      app: whiteboard-ws
   ports:
      - port: 80
        targetPort: 80

```

---

## [whiteboard-configmap.yml](./whiteboard-configmap.yml)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
   name: whiteboard-be
   namespace: whiteboard
data:
   DB_TYPE: 'postgres'
   DB_HOST: 'whiteboard-db-postgresql.database.svc.cluster.local'
   DB_PORT: '5432'
   DB_USERNAME: 'whiteboard'
   DB_PASSWORD: '<WHITEBOARD_DB_PASSWORD>'
   DB_DATABASE: 'whiteboard'
   CLIENT_BASE_URL: 'https://wb-dashboard.dungxbuif.com'
   GOOGLE_CLIENT_ID: '<GOOGLE_CLIENT_ID>'
   GOOGLE_CLIENT_SECRET: '<GOOGLE_CLIENT_SECRET>'
   CORS_ORIGIN: 'https://wb-dashboard.dungxbuif.com,https://whiteboard.dungxbuif.com'
   MINIO_ENDPOINT: storage.dungxbuif.com
   MINIO_ACCESS_KEY: OifL44xAwujtz7pmLcn0
   MINIO_SECRET_KEY: <WHITEBOARD_MINIO_SECRET_KEY>
   MINIO_BUCKET_NAME: whiteboard-sandbox
   NODE_ENV: 'production'
   PORT: '80'
---
apiVersion: v1
kind: ConfigMap
metadata:
   name: whiteboard-ws-config
   namespace: whiteboard
data:
   NODE_ENV: 'production'
   PORT: '80'
   CORS_ORIGIN: 'https://whiteboard.dungxbuif.com'

```

---

## [whiteboard-database.values.yml](./whiteboard-database.values.yml)

```yaml
global:
  storageClass: "longhorn"
  postgresql:
    auth:
      postgresPassword: "<WHITEBOARD_DB_ROOT_PASSWORD>"
      username: "whiteboard"
      password: "<WHITEBOARD_DB_PASSWORD>"
      database: "whiteboard"
      existingSecret: ""
      secretKeys:
        adminPasswordKey: ""
        userPasswordKey: ""
        replicationPasswordKey: ""


auth:
  enablePostgresUser: true

primary:
  resources:
    limits: {}
    requests:
      memory: 512Mi
      cpu: 600m
  
  persistence:
    enabled: true
    storageClass: "longhorn"
    accessModes:
      - ReadWriteOnce
    size: 1Gi
  
```

---

## [whiteboard-ingress.yml](./whiteboard-ingress.yml)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
   name: whiteboard-ingress
   namespace: whiteboard

spec:
   ingressClassName: traefik
   rules:
      - host: whiteboard.dungxbuif.com
        http:
           paths:
              - path: /
                pathType: Prefix
                backend:
                   service:
                      name: whiteboard-fe
                      port:
                         number: 80
      - host: wb-dashboard.dungxbuif.com
        http:
           paths:
              - path: /
                pathType: Prefix
                backend:
                   service:
                      name: whiteboard-dashboard
                      port:
                         number: 80
      - host: api-whiteboard.dungxbuif.com
        http:
           paths:
              - path: /
                pathType: Prefix
                backend:
                   service:
                      name: whiteboard-be
                      port:
                         number: 80
      - host: ws-whiteboard.dungxbuif.com
        http:
           paths:
              - path: /
                pathType: Prefix
                backend:
                   service:
                      name: whiteboard-ws
                      port:
                         number: 80

```

---

## [ws-deployment.yml](./ws-deployment.yml)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
   name: whiteboard-ws
   namespace: whiteboard
spec:
   replicas: 1
   selector:
      matchLabels:
         app: whiteboard-ws
   template:
      metadata:
         labels:
            app: whiteboard-ws
      spec:
         containers:
            - name: whiteboard-ws
              image: registry.dungxbuif.com/whiteboard/whiteboard-ws:latest
              ports:
                 - containerPort: 80
              envFrom:
                 - configMapRef:
                      name: whiteboard-ws-config
         imagePullSecrets:
            - name: regcred

```

---
