```
helm repo add authentik https://charts.goauthentik.io
helm repo update
kubectl create namespace authentik
helm upgrade --install authentik authentik/authentik -f /root/selfhost/kubernetes-v1/authentik/values.yaml -n authentik
```