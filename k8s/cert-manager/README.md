# cert-manager Setup

This folder contains the configuration files for cert-manager and Let's Encrypt certificate issuers.

## Prerequisites

- Kubernetes cluster with nginx-ingress-controller installed
- kubectl configured to access your cluster
- DNS records pointing to your cluster's ingress IP

## Installation Steps

### 1. Install cert-manager

Run the installation script:

```bash
cd k8s/cert-manager
chmod +x install-cert-manager.sh
./install-cert-manager.sh
```

Or manually install:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml
```

Verify installation:

```bash
kubectl get pods -n cert-manager
```

### 2. Configure Email Address

**IMPORTANT:** Before applying the ClusterIssuers, edit the email address in:
- `letsencrypt-prod.yaml`
- `letsencrypt-staging.yaml`

Replace `your-email@example.com` with your actual email address.

### 3. Apply ClusterIssuers

**Start with staging (for testing):**

```bash
kubectl apply -f letsencrypt-staging.yaml
```

**Then apply production:**

```bash
kubectl apply -f letsencrypt-prod.yaml
```

Verify:

```bash
kubectl get clusterissuer
```

### 4. Apply the Ingress Configuration

```bash
kubectl apply -f ../application/synkora-ingress.yml
```

### 5. Check Certificate Status

```bash
# Check certificate
kubectl get certificate -n synkora

# Check certificate details
kubectl describe certificate synkora-api-tls -n synkora

# Check certificate request
kubectl get certificaterequest -n synkora
```

## Troubleshooting

If certificate is not issued:

```bash
# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager

# Check certificate order
kubectl get order -n synkora

# Check challenges
kubectl get challenges -n synkora

# Describe the certificate for more details
kubectl describe certificate synkora-api-tls -n synkora
```

## Testing with Staging

Before using production, test with staging to avoid rate limits:

1. Change annotation in ingress to: `cert-manager.io/cluster-issuer: "letsencrypt-staging"`
2. Apply the ingress
3. Verify certificate is issued (will show as untrusted in browser - this is expected)
4. Once working, switch to `letsencrypt-prod`

## Notes

- Let's Encrypt has rate limits (50 certificates per domain per week for production)
- Use staging environment for testing
- DNS must be properly configured before certificate issuance
- HTTP-01 challenge requires port 80 to be accessible
