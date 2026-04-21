#!/usr/bin/env bash
# Docker helpers: pull, start, health-check, exec wrappers.
# Requires colors.sh and spinner.sh to be sourced first.

DC="docker compose"

# ---------------------------------------------------------------------------
# Pull images (with retries)
# ---------------------------------------------------------------------------
pull_images() {
  section "Pulling Docker images"
  spinner_start "Downloading images (this may take a few minutes on first run)..."

  local attempt=1
  local max=3
  while [ $attempt -le $max ]; do
    if $DC pull --quiet 2>/dev/null; then
      spinner_stop_ok "Images ready"
      return 0
    fi
    spinner_stop
    warn "Pull attempt $attempt/$max failed. Retrying in 10 seconds..."
    sleep 10
    attempt=$((attempt + 1))
    spinner_start "Retrying image pull (attempt $attempt/$max)..."
  done

  spinner_stop_fail "Image pull failed after $max attempts"
  warn "If you are offline and all images are already cached, continuing anyway..."
}

# ---------------------------------------------------------------------------
# Start services
# ---------------------------------------------------------------------------
start_services() {
  section "Starting services"
  spinner_start "Starting Docker containers..."
  if $DC up -d --remove-orphans 2>/tmp/synkora_compose_up.log; then
    spinner_stop_ok "Containers started"
  else
    spinner_stop_fail "docker compose up failed"
    error "Last 20 lines of output:"
    tail -20 /tmp/synkora_compose_up.log >&2
    die "Failed to start services. Check the log above."
  fi
}

# ---------------------------------------------------------------------------
# Wait for PostgreSQL readiness
# ---------------------------------------------------------------------------
wait_for_postgres() {
  section "Waiting for database"
  info "Waiting for PostgreSQL to be ready..."

  local attempts=0
  local max=40  # 80 seconds

  while [ $attempts -lt $max ]; do
    if $DC exec -T postgres pg_isready -U synkora -q 2>/dev/null; then
      success "PostgreSQL is ready"
      return 0
    fi
    attempts=$((attempts + 1))
    printf '.'
    sleep 2
  done

  printf '\n'
  die "PostgreSQL did not become ready after 80 seconds. Check: docker compose logs postgres"
}

# ---------------------------------------------------------------------------
# Wait for API container to be in running state (not full app health —
# just that the container process is up so docker exec works).
# ---------------------------------------------------------------------------
wait_for_api_container() {
  info "Waiting for API container to start..."
  local attempts=0
  local max=60  # 120 seconds — elasticsearch has a 60s start_period

  while [ $attempts -lt $max ]; do
    # 'docker compose exec echo' succeeds only when the container is running
    if $DC exec -T api echo ok >/dev/null 2>&1; then
      success "API container is running"
      return 0
    fi
    attempts=$((attempts + 1))
    printf '.'
    sleep 2
  done

  printf '\n'
  die "API container did not start after 120 seconds. Check: docker compose logs api"
}

# ---------------------------------------------------------------------------
# Wait for API HTTP health endpoint (full app readiness)
# ---------------------------------------------------------------------------
wait_for_api() {
  info "Waiting for API service to be ready..."
  local attempts=0
  local max=30

  while [ $attempts -lt $max ]; do
    if curl -sf http://localhost:5001/health >/dev/null 2>&1; then
      success "API is ready"
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 2
  done

  warn "API health check timed out — continuing anyway"
}

# ---------------------------------------------------------------------------
# Exec wrapper: run a command inside the api container
# ---------------------------------------------------------------------------
api_exec() {
  $DC exec -T api "$@"
}

# Exec with extra env vars — pass each as a separate argument
# Usage: api_exec_env KEY1=val1 KEY2=val2 -- python script.py
api_exec_env() {
  local env_args=""
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do
    env_args="$env_args -e $1"
    shift
  done
  [ $# -gt 0 ] && [ "$1" = "--" ] && shift
  $DC exec -T $env_args api "$@"
}

# ---------------------------------------------------------------------------
# Show container status
# ---------------------------------------------------------------------------
show_status() {
  $DC ps
}

# ---------------------------------------------------------------------------
# Check if services are already running
# ---------------------------------------------------------------------------
services_running() {
  $DC ps --status running 2>/dev/null | grep -q "synkora-api"
}
