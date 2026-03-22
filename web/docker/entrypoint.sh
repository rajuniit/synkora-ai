#!/bin/sh

set -e

echo "Starting Synkora Web..."
echo "Environment: ${DEPLOY_ENV:-development}"
echo "Node Environment: ${NODE_ENV:-production}"

# Check if running in production mode
if [ "${NODE_ENV}" = "production" ]; then
  echo "Running in PRODUCTION mode with PM2"
  
  # Start with PM2 for process management
  exec pm2-runtime start server.js \
    --name synkora-web \
    --instances ${PM2_INSTANCES:-2} \
    --max-memory-restart ${PM2_MAX_MEMORY:-1G}
else
  echo "Running in DEVELOPMENT mode with hot reload"
  
  # Development mode with hot reload
  exec pnpm dev
fi
