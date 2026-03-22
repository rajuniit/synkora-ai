# Load Testing Infrastructure - Isolated Deployment

This directory contains Kubernetes manifests for deploying the load testing infrastructure **separately** from the main Synkora platform.

## Why Isolated Deployment?

During load testing, the LLM Proxy and K6 runners can handle **thousands of requests per second**. Running these on the same infrastructure as the main platform would cause:

- CPU/Memory contention
- Network saturation
- Database connection exhaustion
- Degraded user experience on the main platform

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              KUBERNETES CLUSTER                                  │
│                                                                                  │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────────────┐ │
│  │     NAMESPACE: default          │    │     NAMESPACE: load-testing         │ │
│  │     (Main Platform)             │    │     (Isolated)                      │ │
│  │                                 │    │                                      │ │
│  │  ┌─────────────┐ ┌───────────┐ │    │  ┌─────────────────────────────────┐│ │
│  │  │  Synkora    │ │  Synkora  │ │    │  │        LLM PROXY PODS           ││ │
│  │  │    API      │ │    Web    │ │    │  │  ┌─────┐ ┌─────┐ ┌─────┐       ││ │
│  │  └─────────────┘ └───────────┘ │    │  │  │ P-1 │ │ P-2 │ │ P-N │       ││ │
│  │                                 │    │  │  └─────┘ └─────┘ └─────┘       ││ │
│  │  ┌─────────────┐ ┌───────────┐ │    │  │       (HPA: 3-50 replicas)      ││ │
│  │  │  PostgreSQL │ │   Redis   │ │    │  └─────────────────────────────────┘│ │
│  │  │   (Main)    │ │  (Main)   │ │    │                                      │ │
│  │  └─────────────┘ └───────────┘ │    │  ┌─────────────────────────────────┐│ │
│  │                                 │    │  │        K6 RUNNER PODS           ││ │
│  │  Protected from load testing   │    │  │  ┌─────┐ ┌─────┐               ││ │
│  │  traffic and resource usage    │    │  │  │ K-1 │ │ K-2 │               ││ │
│  │                                 │    │  │  └─────┘ └─────┘               ││ │
│  └─────────────────────────────────┘    │  └─────────────────────────────────┘│ │
│                                          │                                      │ │
│                                          │  ┌─────────────────────────────────┐│ │
│                                          │  │    Redis (Rate Limiting)        ││ │
│                                          │  └─────────────────────────────────┘│ │
│                                          └─────────────────────────────────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

                    │                                    │
                    │                                    │
                    ▼                                    ▼
            ┌───────────────┐                  ┌─────────────────────┐
            │   Internet    │                  │  proxy.synkora.com  │
            │   Users       │                  │  (Load Balancer)    │
            └───────────────┘                  └─────────────────────┘
```

## Request Flow During Load Testing

```
┌──────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Synkora    │────▶│  K6 Runner Pod  │────▶│  User's Agent   │────▶│  LLM Proxy Pod  │
│   Platform   │     │  (Isolated)     │     │  (External)     │     │  (Isolated)     │
│              │     │                 │     │                 │     │                 │
│  Triggers    │     │  Generates      │     │  Receives       │     │  Returns mock   │
│  test run    │     │  HTTP requests  │     │  load traffic   │     │  LLM responses  │
└──────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                                                                              │
                                                                              │
                                                                              ▼
                                                                     ┌─────────────────┐
                                                                     │  No real LLM    │
                                                                     │  API calls!     │
                                                                     │  No costs!      │
                                                                     └─────────────────┘
```

## Deployment

### 1. Create the namespace and deploy Redis

```bash
kubectl apply -f redis-deployment.yaml
```

### 2. Update secrets with your actual values

```bash
kubectl edit secret llm-proxy-secrets -n load-testing
```

### 3. Deploy the LLM Proxy

```bash
kubectl apply -f proxy-deployment.yaml
```

### 4. Deploy K6 Runners

```bash
kubectl apply -f k6-runner-deployment.yaml
```

### 5. Verify deployment

```bash
kubectl get pods -n load-testing
kubectl get svc -n load-testing
```

## Configuration

### Scaling

The LLM Proxy uses HPA (Horizontal Pod Autoscaler) to automatically scale:
- **Min replicas**: 3
- **Max replicas**: 50
- **Scale up trigger**: CPU > 70% or Memory > 80%
- **Scale up speed**: Up to 100% more pods every 30 seconds

### Resource Limits

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| LLM Proxy | 500m | 2000m | 512Mi | 2Gi |
| K6 Runner | 1000m | 4000m | 1Gi | 4Gi |
| Redis | 100m | 500m | 256Mi | 512Mi |

### Dedicated Node Pool (Recommended)

For production, create a dedicated node pool for load testing:

```bash
# GKE example
gcloud container node-pools create load-testing-pool \
  --cluster=your-cluster \
  --num-nodes=3 \
  --machine-type=n2-standard-4 \
  --node-labels=node-type=load-testing \
  --node-taints=load-testing=true:NoSchedule
```

## DNS Configuration

Point your proxy domain to the LoadBalancer:

```
proxy.synkora.com  →  LLM Proxy LoadBalancer IP
```

## Monitoring

The proxy exposes Prometheus metrics at `/metrics`:

```yaml
# Prometheus scrape config
- job_name: 'llm-proxy'
  kubernetes_sd_configs:
    - role: pod
      namespaces:
        names: ['load-testing']
  relabel_configs:
    - source_labels: [__meta_kubernetes_pod_label_app]
      regex: llm-proxy
      action: keep
```

## Cleanup

To remove all load testing infrastructure:

```bash
kubectl delete namespace load-testing
```
