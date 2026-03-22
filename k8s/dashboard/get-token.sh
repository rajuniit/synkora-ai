#!/bin/bash

echo "Getting bearer token for Kubernetes Dashboard..."
echo ""

# Create token for admin-user
TOKEN=$(kubectl -n kubernetes-dashboard create token admin-user --duration=87600h)

echo "Your bearer token (valid for 10 years):"
echo ""
echo "$TOKEN"
echo ""
echo "Copy this token to login to the dashboard"
