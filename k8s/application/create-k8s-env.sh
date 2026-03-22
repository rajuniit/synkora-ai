#!/bin/bash
# Script to create Kubernetes ConfigMap and Secrets from API .env file
# Usage: ./create-k8s-env.sh

set -e

NAMESPACE="synkora-production"
ENV_FILE=".env"
CONFIGMAP_NAME="synkora-config"
SECRET_NAME="synkora-secrets"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found"
    echo "Make sure you run this script from the k8s/application directory"
    exit 1
fi

echo "Creating Kubernetes namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

echo "Creating Secret from .env file..."
# All environment variables will be stored as secrets for security

# Create Secret directly from .env file
kubectl create secret generic $SECRET_NAME \
    --from-env-file=$ENV_FILE \
    -n $NAMESPACE \
    --dry-run=client \
    -o yaml | kubectl apply -f -

echo "✓ Secret '$SECRET_NAME' created/updated with all environment variables"

echo ""
echo "✓ Kubernetes environment setup complete!"
echo ""
echo "Verify with:"
echo "  kubectl get configmap -n $NAMESPACE"
echo "  kubectl get secret -n $NAMESPACE"
echo ""
