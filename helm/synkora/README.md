# Synkora Helm Chart

This Helm chart deploys Synkora on Kubernetes, following the patterns established by Synkora's community Helm charts.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- PV provisioner support in the underlying infrastructure
- AWS Load Balancer Controller (for AWS EKS deployments)

## Installing the Chart

### Add Bitnami Repository

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### Install Dependencies

```bash
cd helm/synkora
helm dependency update
```

### Install the Chart

```bash
helm install synkora . \
  --namespace synkora \
  --create-namespace \
  --values values.yaml
```

### Install with Custom Values

```bash
helm install synkora . \
  --namespace synkora \
  --create-namespace \
  --set api.image.repository=<YOUR_ECR_REPO>/synkora-api \
  --set web.image.repository=<YOUR_ECR_REPO>/synkora-web \
  --set postgresql.auth.password=<YOUR_DB_PASSWORD> \
  --set redis.auth.password=<YOUR_REDIS_PASSWORD>
```

## Uninstalling the Chart

```bash
helm uninstall synkora --namespace synkora
```

## Configuration

The following table lists the configurable parameters and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.storageClass` | Global storage class | `gp3` |

### PostgreSQL Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.auth.username` | PostgreSQL username | `synkora` |
| `postgresql.auth.password` | PostgreSQL password | `changeme` |
| `postgresql.auth.database` | PostgreSQL database | `synkora` |
| `postgresql.primary.persistence.size` | PostgreSQL PVC size | `20Gi` |

### Redis Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis | `true` |
| `redis.auth.password` | Redis password | `changeme` |
| `redis.master.persistence.size` | Redis PVC size | `8Gi` |

### API Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.enabled` | Enable API deployment | `true` |
| `api.replicaCount` | Number of API replicas | `3` |
| `api.image.repository` | API image repository | `<YOUR_ECR_REPO>/synkora-api` |
| `api.image.tag` | API image tag | `latest` |
| `api.autoscaling.enabled` | Enable HPA for API | `true` |
| `api.autoscaling.minReplicas` | Minimum API replicas | `3` |
| `api.autoscaling.maxReplicas` | Maximum API replicas | `10` |

### Web Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `web.enabled` | Enable Web deployment | `true` |
| `web.replicaCount` | Number of Web replicas | `2` |
| `web.image.repository` | Web image repository | `<YOUR_ECR_REPO>/synkora-web` |
| `web.image.tag` | Web image tag | `latest` |
| `web.autoscaling.enabled` | Enable HPA for Web | `true` |

### Worker Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `worker.enabled` | Enable Worker deployment | `true` |
| `worker.replicaCount` | Number of Worker replicas | `2` |
| `worker.autoscaling.enabled` | Enable HPA for Worker | `true` |

### Ingress Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `alb` |
| `ingress.hosts[0].host` | Hostname | `synkora.yourdomain.com` |

## Examples

### Production Deployment on AWS EKS

```bash
helm install synkora . \
  --namespace synkora \
  --create-namespace \
  --set api.image.repository=123456789.dkr.ecr.us-east-1.amazonaws.com/synkora-api \
  --set web.image.repository=123456789.dkr.ecr.us-east-1.amazonaws.com/synkora-web \
  --set worker.image.repository=123456789.dkr.ecr.us-east-1.amazonaws.com/synkora-api \
  --set postgresql.auth.password=SecurePassword123 \
  --set redis.auth.password=SecureRedisPass456 \
  --set ingress.annotations."alb\.ingress\.kubernetes\.io/certificate-arn"=arn:aws:acm:us-east-1:123456789:certificate/xxx \
  --set ingress.hosts[0].host=synkora.example.com
```

### Development Deployment

```bash
helm install synkora . \
  --namespace synkora-dev \
  --create-namespace \
  --set api.replicaCount=1 \
  --set web.replicaCount=1 \
  --set worker.replicaCount=1 \
  --set api.autoscaling.enabled=false \
  --set web.autoscaling.enabled=false \
  --set worker.autoscaling.enabled=false \
  --set postgresql.primary.persistence.size=10Gi \
  --set redis.master.persistence.size=2Gi
```

## Upgrading

```bash
helm upgrade synkora . \
  --namespace synkora \
  --values values.yaml
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n synkora
```

### View Pod Logs

```bash
kubectl logs -n synkora <pod-name>
```

### Describe Pod

```bash
kubectl describe pod -n synkora <pod-name>
```

### Check Ingress

```bash
kubectl get ingress -n synkora
kubectl describe ingress -n synkora synkora
```

## References

- [Synkora Community Helm Charts](https://github.com/douban/charts/tree/master/charts/synkora)
- [Bitnami PostgreSQL Chart](https://github.com/bitnami/charts/tree/main/bitnami/postgresql)
- [Bitnami Redis Chart](https://github.com/bitnami/charts/tree/main/bitnami/redis)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
