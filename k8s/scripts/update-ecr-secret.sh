#!/bin/bash

AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="614209211965"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Get ECR login token
TOKEN=$(aws ecr get-login-password --region ${AWS_REGION})

# Delete existing secret if it exists
kubectl delete secret ecr-registry-secret -n synkora-production --ignore-not-found

# Create new secret
kubectl create secret docker-registry ecr-registry-secret \
  --docker-server=${ECR_REGISTRY} \
  --docker-username=AWS \
  --docker-password=${TOKEN} \
  --namespace=synkora-production

echo "ECR secret updated successfully!"