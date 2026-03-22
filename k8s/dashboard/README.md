# Kubernetes Dashboard Setup

This directory contains scripts and configuration for deploying Kubernetes Dashboard.

## Installation Steps

### 1. Install Kubernetes Dashboard

```bash
cd /Users/pappu/Desktop/synkora/k8s/dashboard
chmod +x install-dashboard.sh
./install-dashboard.sh
```

### 2. Create Admin User

```bash
kubectl apply -f dashboard-adminuser.yaml
```

### 3. Get Access Token

```bash
chmod +x get-token.sh
./get-token.sh
```

Copy the token output - you'll need it to login to the dashboard.

### 4. Access the Dashboard

#### Option A: Via kubectl proxy (Local Access)

```bash
kubectl proxy
```

Then open: http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/

#### Option B: Via Ingress (Public Access with HTTPS)

```bash
# Apply the ingress
kubectl apply -f dashboard-ingress.yaml

# Add DNS record for dashboard.synkora.ai pointing to your ingress IP
# Wait for certificate to be issued
kubectl get certificate -n kubernetes-dashboard

# Access at: https://dashboard.synkora.ai
```

### 5. Login

1. Select "Token" authentication method
2. Paste the token you got from `get-token.sh`
3. Click "Sign in"

## Features

- View and manage pods, deployments, services
- Check pod logs in real-time
- Execute shell commands in pods
- View resource usage (CPU, Memory)
- Monitor cluster health
- Manage ConfigMaps and Secrets

## Security Notes

- The admin-user has cluster-admin privileges (full access)
- Token is valid for 10 years - store it securely
- For production, consider more restrictive RBAC policies
- Use ingress with proper authentication for public access

## Troubleshooting

### Check dashboard pods
```bash
kubectl get pods -n kubernetes-dashboard
```

### Check dashboard logs
```bash
kubectl logs -n kubernetes-dashboard -l k8s-app=kubernetes-dashboard
```

### Restart dashboard
```bash
kubectl rollout restart deployment/kubernetes-dashboard -n kubernetes-dashboard
```

### Delete and reinstall
```bash
kubectl delete namespace kubernetes-dashboard
./install-dashboard.sh
```

## Alternative: K9s CLI Tool

For a terminal-based alternative, install k9s:

```bash
# macOS
brew install k9s

# Run k9s
k9s -n synkora
```

K9s features:
- Terminal-based UI
- Real-time pod logs
- Resource monitoring
- Quick navigation
- Shell access to pods
- No authentication needed
