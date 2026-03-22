# Kubernetes Deployment Guide

This directory contains Kubernetes manifests and Helm charts for deploying Synkora to production.

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.x
- Docker registry access
- Domain name with SSL certificate

## Quick Start

### 1. Install with Helm

```bash
# Add Helm repository (if using)
helm repo add synkora ./helm/synkora
helm repo update

# Install Synkora
helm install synkora ./helm/synkora \
  --namespace synkora \
  --create-namespace \
  --values ./helm/synkora/values.yaml
```

### 2. Manual Deployment

```bash
# Create namespace
kubectl create namespace synkora

# Apply configurations
kubectl apply -f ./base/namespace.yaml
kubectl apply -f ./base/configmap.yaml
kubectl apply -f ./base/secrets.yaml

# Deploy infrastructure
kubectl apply -f ./infrastructure/

# Deploy application
kubectl apply -f ./application/
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                        │
│                    (Ingress/ALB)                         │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼────┐            ┌────▼────┐
    │   Web   │            │   API   │
    │ (Next)  │            │ (Flask) │
    └────┬────┘            └────┬────┘
         │                      │
         │         ┌────────────┴────────────┐
         │         │                         │
    ┌────▼────┐   ▼                    ┌────▼────┐
    │  Redis  │  PostgreSQL            │ Celery  │
    │ (Cache) │  (Database)            │ Worker  │
    └─────────┘                        └─────────┘
```

## Components

### Application Services
- **Web**: Next.js frontend (3 replicas)
- **API**: Flask backend (3 replicas)
- **Worker**: Celery workers (2 replicas)

### Infrastructure
- **PostgreSQL**: Primary database (StatefulSet)
- **Redis**: Cache and message broker (StatefulSet)
- **Nginx**: Reverse proxy and static files

### Storage
- **PVC**: Persistent volumes for uploads and data
- **S3**: Object storage for files (optional)

## Configuration

### Environment Variables

Create a `secrets.yaml` file:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: synkora-secrets
  namespace: synkora
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@postgres:5432/synkora"
  REDIS_URL: "redis://redis:6379/0"
  SECRET_KEY: "your-secret-key-here"
  OPENAI_API_KEY: "your-openai-key"
```

### Scaling

```bash
# Scale API
kubectl scale deployment synkora-api --replicas=5 -n synkora

# Scale Workers
kubectl scale deployment synkora-worker --replicas=3 -n synkora

# Scale Web
kubectl scale deployment synkora-web --replicas=5 -n synkora
```

## Monitoring

### Health Checks

```bash
# Check pod status
kubectl get pods -n synkora

# Check logs
kubectl logs -f deployment/synkora-api -n synkora
kubectl logs -f deployment/synkora-web -n synkora
kubectl logs -f deployment/synkora-worker -n synkora
```

### Metrics

Prometheus metrics are exposed at:
- API: `/metrics`
- Web: `/api/metrics`

## Backup & Recovery

### Database Backup

```bash
# Backup
kubectl exec -n synkora postgres-0 -- pg_dump -U synkora synkora > backup.sql

# Restore
kubectl exec -i -n synkora postgres-0 -- psql -U synkora synkora < backup.sql
```

### Volume Backup

```bash
# Backup PVC
kubectl get pvc -n synkora
# Use your cloud provider's snapshot feature
```

## Troubleshooting

### Common Issues

1. **Pods not starting**
   ```bash
   kubectl describe pod <pod-name> -n synkora
   kubectl logs <pod-name> -n synkora
   ```

2. **Database connection issues**
   ```bash
   kubectl exec -it deployment/synkora-api -n synkora -- env | grep DATABASE
   ```

3. **Storage issues**
   ```bash
   kubectl get pvc -n synkora
   kubectl describe pvc <pvc-name> -n synkora
   ```

## Security

- All secrets are stored in Kubernetes Secrets
- Network policies restrict pod-to-pod communication
- RBAC is configured for service accounts
- TLS/SSL is enforced via Ingress

## Updates

### Rolling Update

```bash
# Update API
kubectl set image deployment/synkora-api api=synkora/api:v2.0.0 -n synkora

# Update Web
kubectl set image deployment/synkora-web web=synkora/web:v2.0.0 -n synkora

# Check rollout status
kubectl rollout status deployment/synkora-api -n synkora
```

### Rollback

```bash
kubectl rollout undo deployment/synkora-api -n synkora
kubectl rollout undo deployment/synkora-web -n synkora
```

## Production Checklist

- [ ] SSL certificates configured
- [ ] Database backups automated
- [ ] Monitoring and alerting set up
- [ ] Resource limits configured
- [ ] Horizontal Pod Autoscaling enabled
- [ ] Network policies applied
- [ ] Secrets rotated
- [ ] Disaster recovery plan documented
- [ ] Load testing completed
- [ ] Security scan passed
