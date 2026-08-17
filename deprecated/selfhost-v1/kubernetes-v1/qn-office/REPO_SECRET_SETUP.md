# Setup ArgoCD Access to Private Repo (HTTPS Token)

## 1. Generate GitHub Personal Access Token (PAT)
- Go to: https://github.com/settings/tokens
- Generate new token (classic)
- Scopes: `repo` (Full control of private repositories)
- Copy the token.

## 2. Create Kubernetes Secret
Run the following command (Replace `YOUR_GITHUB_TOKEN`):

```bash
kubectl create secret generic qn-office-repo-creds \
  --namespace=argocd \
  --from-literal=url=https://github.com/dungxbuif-ncc/QnOffice.git \
  --from-literal=username=not-used \
  --from-literal=password=YOUR_GITHUB_TOKEN \
  --from-literal=type=git \
  --dry-run=client -o yaml | \
  kubectl label --local -f - "argocd.argoproj.io/secret-type=repository" -o yaml | \
  kubectl apply -f -
```

## 3. Verify
Check if ArgoCD recognizes the repo:

```bash
kubectl get secret qn-office-repo-creds -n argocd --show-labels
# Should show label: argocd.argoproj.io/secret-type=repository
```
