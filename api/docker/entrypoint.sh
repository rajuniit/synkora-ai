#!/bin/bash

set -e

# Set UTF-8 encoding to address potential encoding issues in containerized environments
export LANG=${LANG:-en_US.UTF-8}
export LC_ALL=${LC_ALL:-en_US.UTF-8}
export PYTHONIOENCODING=${PYTHONIOENCODING:-utf-8}

echo "Starting Synkora API..."
echo "Mode: ${MODE:-api}"
echo "Environment: ${DEPLOY_ENV:-development}"

# Run migrations if enabled
if [[ "${MIGRATION_ENABLED}" == "true" ]]; then
  echo "Running database migrations..."
  alembic upgrade head
  
  # Pure migration mode - exit after migrations
  if [[ "${MODE}" == "migration" ]]; then
    echo "Migration completed, exiting normally"
    exit 0
  fi
fi

# Start the appropriate service based on MODE
if [[ "${MODE}" == "worker" ]]; then
  echo "Starting Celery worker..."
  
  # Get the number of available CPU cores for auto-scaling
  if [ "${CELERY_AUTO_SCALE,,}" = "true" ]; then
    AVAILABLE_CORES=$(nproc)
    MAX_WORKERS=${CELERY_MAX_WORKERS:-$AVAILABLE_CORES}
    MIN_WORKERS=${CELERY_MIN_WORKERS:-1}
    CONCURRENCY_OPTION="--autoscale=${MAX_WORKERS},${MIN_WORKERS}"
  else
    CONCURRENCY_OPTION="-c ${CELERY_WORKER_AMOUNT:-1}"
  fi
  
  exec celery -A src.config.celery worker \
    -P ${CELERY_WORKER_CLASS:-gevent} \
    $CONCURRENCY_OPTION \
    --max-tasks-per-child ${MAX_TASKS_PER_CHILD:-50} \
    --loglevel ${LOG_LEVEL:-INFO} \
    -Q ${CELERY_QUEUES:-default,document_processing}

elif [[ "${MODE}" == "beat" ]]; then
  echo "Starting Celery beat scheduler..."
  exec celery -A src.config.celery beat --loglevel ${LOG_LEVEL:-INFO}

else
  # API mode (default)
  echo "Starting API server..."
  
  if [[ "${DEBUG}" == "true" ]]; then
    # Development mode with hot reload
    echo "Running in DEBUG mode with hot reload"
    exec uvicorn app:app \
      --host ${DIFY_BIND_ADDRESS:-0.0.0.0} \
      --port ${DIFY_PORT:-5001} \
      --reload
  else
    # Production mode with Gunicorn
    echo "Running in PRODUCTION mode"
    exec gunicorn app:app \
      --bind "${DIFY_BIND_ADDRESS:-0.0.0.0}:${DIFY_PORT:-5001}" \
      --workers ${SERVER_WORKER_AMOUNT:-4} \
      --worker-class ${SERVER_WORKER_CLASS:-uvicorn.workers.UvicornWorker} \
      --timeout ${GUNICORN_TIMEOUT:-120} \
      --access-logfile - \
      --error-logfile - \
      --log-level ${LOG_LEVEL:-info}
  fi
fi
