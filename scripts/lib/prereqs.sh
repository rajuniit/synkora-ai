#!/usr/bin/env bash
# Prerequisite checks and optional installation helpers.
# Requires colors.sh to be sourced first.

# ---------------------------------------------------------------------------
# OS / Arch detection
# ---------------------------------------------------------------------------
detect_os() {
  OS="$(uname -s)"
  ARCH="$(uname -m)"
  DISTRO=""

  if [ "$OS" = "Linux" ] && [ -f /etc/os-release ]; then
    DISTRO="$(. /etc/os-release && echo "${ID:-unknown}")"
  fi

  export OS ARCH DISTRO
}

# ---------------------------------------------------------------------------
# Individual tool checks
# ---------------------------------------------------------------------------
has_cmd() { command -v "$1" >/dev/null 2>&1; }

check_docker() {
  if ! has_cmd docker; then
    cross "Docker not found"
    return 1
  fi

  # Verify daemon is running
  if ! docker info >/dev/null 2>&1; then
    cross "Docker is installed but not running"
    warn "  Mac:   Open Docker Desktop and wait for it to start"
    warn "  Linux: sudo systemctl start docker"
    return 1
  fi

  # Require Compose v2 (plugin)
  if ! docker compose version >/dev/null 2>&1; then
    cross "Docker Compose v2 plugin not found (need 'docker compose', not 'docker-compose')"
    return 1
  fi

  check "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
  check "Docker Compose $(docker compose version --short 2>/dev/null || echo 'v2')"
  return 0
}

check_openssl() {
  if has_cmd openssl; then
    check "openssl $(openssl version | awk '{print $2}')"
    return 0
  fi
  cross "openssl not found"
  return 1
}

check_git() {
  if has_cmd git; then
    check "git $(git --version | awk '{print $3}')"
    return 0
  fi
  cross "git not found"
  return 1
}

check_node() {
  if ! has_cmd node; then
    cross "Node.js not found"
    return 1
  fi
  local ver
  ver="$(node --version | tr -d 'v')"
  local major
  major="$(echo "$ver" | cut -d. -f1)"
  if [ "$major" -lt 20 ]; then
    cross "Node.js $ver found, but version 20+ is required"
    return 1
  fi
  check "Node.js v$ver"
  return 0
}

check_pnpm() {
  if has_cmd pnpm; then
    check "pnpm $(pnpm --version)"
    return 0
  fi
  cross "pnpm not found"
  return 1
}

# ---------------------------------------------------------------------------
# Port conflict detection
# ---------------------------------------------------------------------------
port_in_use() {
  # returns 0 if port is occupied
  if has_cmd lsof; then
    lsof -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1
  elif has_cmd ss; then
    ss -tlnH "sport = :$1" 2>/dev/null | grep -q .
  else
    (echo "" >/dev/tcp/127.0.0.1/"$1") 2>/dev/null
  fi
}

check_ports() {
  local failed=0
  for port in 5001 5438 6379 9000 9001 3001; do
    if port_in_use "$port"; then
      warn "Port $port is already in use — may conflict with Synkora services"
      failed=1
    fi
  done
  return $failed
}

# ---------------------------------------------------------------------------
# Install helpers (best-effort, not required for offline installs)
# ---------------------------------------------------------------------------
install_docker_mac() {
  if has_cmd brew; then
    info "Installing Docker Desktop via Homebrew..."
    brew install --cask docker
  else
    die "Please install Docker Desktop from https://docs.docker.com/desktop/install/mac/"
  fi
}

install_docker_linux() {
  case "$DISTRO" in
    ubuntu|debian)
      info "Installing Docker via apt..."
      sudo apt-get update -qq
      sudo apt-get install -y -qq ca-certificates curl
      sudo install -m 0755 -d /etc/apt/keyrings
      sudo curl -fsSL https://download.docker.com/linux/"$DISTRO"/gpg \
        -o /etc/apt/keyrings/docker.asc
      sudo chmod a+r /etc/apt/keyrings/docker.asc
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/$DISTRO $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
      sudo apt-get update -qq
      sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
      sudo systemctl enable --now docker
      sudo usermod -aG docker "$USER"
      warn "You may need to log out and back in for docker group changes to take effect"
      ;;
    fedora|rhel|centos)
      sudo dnf -y install docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
      sudo systemctl enable --now docker
      ;;
    arch|manjaro)
      sudo pacman -Sy --noconfirm docker docker-compose
      sudo systemctl enable --now docker
      ;;
    *)
      die "Unsupported distro '$DISTRO'. Install Docker manually: https://docs.docker.com/engine/install/"
      ;;
  esac
}

maybe_install_docker() {
  warn "Docker is required to run Synkora."
  # In non-interactive mode, fail immediately instead of prompting
  if [ "${NON_INTERACTIVE:-false}" = "true" ]; then
    die "Docker not found. Install Docker and re-run in non-interactive mode."
  fi
  printf '  Install Docker now? [y/N] '
  read -r ans
  case "$ans" in
    [Yy]*)
      if [ "$OS" = "Darwin" ]; then
        install_docker_mac
      else
        install_docker_linux
      fi
      ;;
    *)
      die "Please install Docker and re-run ./install.sh"
      ;;
  esac
}

# ---------------------------------------------------------------------------
# System resource checks
# ---------------------------------------------------------------------------
get_ram_mb() {
  if [ "$OS" = "Darwin" ]; then
    # sysctl returns bytes; convert to MB
    sysctl -n hw.memsize 2>/dev/null | awk '{printf "%d", $1/1024/1024}'
  else
    # /proc/meminfo MemTotal is in kB
    awk '/^MemTotal:/ {printf "%d", $2/1024}' /proc/meminfo 2>/dev/null
  fi
}

get_free_disk_mb() {
  # df -k: column 4 is available in 1024-byte blocks on both Linux and macOS
  df -k "$REPO_ROOT" 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}'
}

get_cpu_count() {
  if [ "$OS" = "Darwin" ]; then
    sysctl -n hw.logicalcpu 2>/dev/null || echo "?"
  else
    nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo "?"
  fi
}

check_resources() {
  section "Checking system resources"

  local ram_mb cpu_count free_disk_mb
  ram_mb="$(get_ram_mb)"
  cpu_count="$(get_cpu_count)"
  free_disk_mb="$(get_free_disk_mb)"

  # RAM check — minimum 8 GB, recommended 16 GB
  local ram_gb="?"
  if [ -n "$ram_mb" ] && [ "$ram_mb" -gt 0 ] 2>/dev/null; then
    ram_gb=$(( ram_mb / 1024 ))
    if [ "$ram_mb" -lt 8192 ]; then
      cross "RAM: ${ram_gb} GB detected — Synkora requires at least 8 GB (16 GB recommended)"
      warn "  Elasticsearch alone is hard-capped at 2 GB; services will likely OOM."
      warn "  Add more RAM or reduce running services before continuing."
      if [ "${NON_INTERACTIVE:-false}" = "true" ]; then
        die "Insufficient RAM. Need at least 8 GB."
      fi
      printf '  Continue anyway? [y/N] '
      read -r _ans
      case "$_ans" in
        [Yy]*) warn "Continuing with low RAM — expect instability." ;;
        *)     die "Aborted. Add more RAM and re-run ./install.sh" ;;
      esac
    elif [ "$ram_mb" -lt 16384 ]; then
      warn "RAM: ${ram_gb} GB — meets minimum but 16 GB is recommended for stable operation"
    else
      check "RAM: ${ram_gb} GB"
    fi
  else
    warn "Could not determine available RAM — proceeding anyway"
  fi

  # CPU check — informational only, warn if < 4
  if [ "$cpu_count" != "?" ] && [ "$cpu_count" -lt 4 ] 2>/dev/null; then
    warn "CPU: ${cpu_count} core(s) — 4+ cores recommended (Celery runs 16 concurrent tasks)"
  else
    check "CPU: ${cpu_count} core(s)"
  fi

  # Disk check — minimum 40 GB free
  local free_disk_gb="?"
  if [ -n "$free_disk_mb" ] && [ "$free_disk_mb" -gt 0 ] 2>/dev/null; then
    free_disk_gb=$(( free_disk_mb / 1024 ))
    if [ "$free_disk_mb" -lt 20480 ]; then
      cross "Free disk: ${free_disk_gb} GB — minimum 20 GB required (40 GB recommended)"
      warn "  Docker images alone take ~15 GB; data volumes grow over time."
      if [ "${NON_INTERACTIVE:-false}" = "true" ]; then
        die "Insufficient disk space. Need at least 20 GB free (40 GB recommended)."
      fi
      printf '  Continue anyway? [y/N] '
      read -r _ans
      case "$_ans" in
        [Yy]*) warn "Continuing with low disk — pull or startup may fail." ;;
        *)     die "Aborted. Free up disk space and re-run ./install.sh" ;;
      esac
    elif [ "$free_disk_mb" -lt 40960 ]; then
      warn "Free disk: ${free_disk_gb} GB — 40 GB free is recommended (you have ${free_disk_gb} GB)"
    else
      check "Free disk: ${free_disk_gb} GB"
    fi
  else
    warn "Could not determine free disk space — proceeding anyway"
  fi
}

# ---------------------------------------------------------------------------
# Run all prerequisite checks
# ---------------------------------------------------------------------------
check_prerequisites() {
  section "Checking prerequisites"

  local docker_ok=0 openssl_ok=0 node_ok=0 pnpm_ok=0

  check_docker    || docker_ok=1
  check_openssl   || openssl_ok=1
  check_git       || true  # git is optional if already in the repo

  if [ $docker_ok -ne 0 ]; then
    maybe_install_docker
    check_docker || die "Docker installation failed. Please install manually."
  fi

  if [ $openssl_ok -ne 0 ]; then
    die "openssl is required for key generation. Install it and re-run ./install.sh"
  fi

  # Node + pnpm: only required for local frontend mode
  if [ "${FRONTEND_MODE:-local}" = "local" ]; then
    check_node  || node_ok=1
    check_pnpm  || pnpm_ok=1

    if [ $node_ok -ne 0 ] || [ $pnpm_ok -ne 0 ]; then
      warn "Node.js 20+ and pnpm are required for local frontend."
      if [ "${NON_INTERACTIVE:-false}" = "true" ]; then
        warn "Non-interactive mode: switching to Docker frontend automatically."
        FRONTEND_MODE=docker
      else
        printf '  Use Docker for the frontend instead? [Y/n] '
        read -r ans
        case "$ans" in
          [Nn]*) die "Install Node.js 20+ (https://nodejs.org) and pnpm (npm i -g pnpm), then re-run." ;;
          *)     FRONTEND_MODE=docker ;;
        esac
      fi
    fi
  fi

  check_ports || true  # port conflicts are warnings, not fatal

  success "Prerequisites OK"
}
