#!/bin/bash

echo "Installing Kubernetes Dashboard..."

# Apply Kubernetes Dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Wait for dashboard to be ready
echo "Waiting for dashboard to be ready..."
kubectl wait --for=condition=ready pod -l k8s-app=kubernetes-dashboard -n kubernetes-dashboard --timeout=300s

echo "Kubernetes Dashboard installed successfully!"
echo ""
echo "To access the dashboard, run:"
echo "kubectl proxy"
echo ""
echo "Then access at: http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/"
