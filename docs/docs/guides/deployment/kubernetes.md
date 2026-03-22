---
sidebar_position: 2
---

# Kubernetes Deployment

Deploy Synkora on Kubernetes with Helm.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.0+
- kubectl configured

## Install with Helm

```bash
# Add repository
helm repo add synkora https://charts.synkora.io
helm repo update

# Create namespace
kubectl create namespace synkora

# Create secrets
kubectl create secret generic synkora-secrets \
  --namespace synkora \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=OPENAI_API_KEY=sk-xxx \
  --from-literal=DATABASE_URL=postgresql://...

# Install
helm install synkora synkora/synkora \
  --namespace synkora \
  --values values.yaml
```

## values.yaml

```yaml
global:
  domain: synkora.example.com

api:
  replicas: 3
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "2Gi"
      cpu: "1000m"

web:
  replicas: 2

celery:
  worker:
    replicas: 2
  beat:
    replicas: 1

postgresql:
  enabled: true
  primary:
    persistence:
      size: 50Gi

redis:
  enabled: true

qdrant:
  enabled: true
  persistence:
    size: 20Gi

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: synkora.example.com
  tls:
    - secretName: synkora-tls
      hosts:
        - synkora.example.com
```

## Scaling

```bash
kubectl scale deployment synkora-api --replicas=5 -n synkora
```

## Monitoring

```bash
kubectl logs -f deployment/synkora-api -n synkora
kubectl get pods -n synkora
```

## Next Steps

- [Production checklist](/docs/guides/deployment/production)
