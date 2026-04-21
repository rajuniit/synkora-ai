#!/usr/bin/env bash
# =============================================================================
# Synkora Installer
# Usage:  ./install.sh                   (interactive)
#         ./install.sh --non-interactive  (CI/CD — reads SYNKORA_* env vars)
# =============================================================================
set -euo pipefail

INSTALLER_VERSION="1.0.0"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
export REPO_ROOT

# ---------------------------------------------------------------------------
# Source library scripts
# ---------------------------------------------------------------------------
. "$REPO_ROOT/scripts/lib/colors.sh"
. "$REPO_ROOT/scripts/lib/spinner.sh"
. "$REPO_ROOT/scripts/lib/prereqs.sh"
. "$REPO_ROOT/scripts/lib/env_generator.sh"
. "$REPO_ROOT/scripts/lib/docker_utils.sh"
. "$REPO_ROOT/scripts/lib/seeding.sh"

# ---------------------------------------------------------------------------
# Globals (populated by wizard or non-interactive mode)
# ---------------------------------------------------------------------------
NON_INTERACTIVE=false
FRONTEND_MODE="${FRONTEND_MODE:-local}"   # local | docker

admin_email=""
admin_password=""
admin_name=""
org_name=""
llm_provider=""   # openai | anthropic | skip
llm_api_key=""
slack_bot_token=""
slack_app_token=""
slack_channel="general"

# ---------------------------------------------------------------------------
# Step 0 — Welcome Banner
# ---------------------------------------------------------------------------
show_banner() {
  printf '\n'
  printf '%s' "${BOLD}${CYAN}"
  cat <<'BANNER'
  ███████╗██╗   ██╗███╗   ██╗██╗  ██╗ ██████╗ ██████╗  █████╗
  ██╔════╝╚██╗ ██╔╝████╗  ██║██║ ██╔╝██╔═══██╗██╔══██╗██╔══██╗
  ███████╗ ╚████╔╝ ██╔██╗ ██║█████╔╝ ██║   ██║██████╔╝███████║
  ╚════██║  ╚██╔╝  ██║╚██╗██║██╔═██╗ ██║   ██║██╔══██╗██╔══██║
  ███████║   ██║   ██║ ╚████║██║  ██╗╚██████╔╝██║  ██║██║  ██║
  ╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
BANNER
  printf '%s' "${RESET}"
  printf '\n  %sAI Agent Platform%s  •  Installer v%s\n' "${BOLD}" "${RESET}" "$INSTALLER_VERSION"
  printf '  Estimated time: ~5 minutes\n'
  printf '  Press %sCtrl+C%s at any time to cancel.\n\n' "${BOLD}" "${RESET}"
}

# ---------------------------------------------------------------------------
# Step 3 — Detect Existing Installation
# ---------------------------------------------------------------------------
detect_existing_install() {
  if [ ! -f "$REPO_ROOT/api/.env" ] && ! services_running 2>/dev/null; then
    return 0  # fresh install
  fi

  section "Existing installation detected"
  warn "Found an existing Synkora installation."

  # Non-interactive: always upgrade — never prompt
  if [ "$NON_INTERACTIVE" = true ]; then
    info "Non-interactive mode: upgrading existing installation."
    SKIP_ENV_GEN=true
    SKIP_PULL=false
    return 0
  fi

  printf '\n  %s[U]%s Upgrade   (re-run migrations + seeders, keep data)\n' "${BOLD}" "${RESET}"
  printf '  %s[R]%s Reset     (destroy all containers + volumes, start fresh)\n' "${BOLD}" "${RESET}"
  printf '  %s[Q]%s Quit\n\n' "${BOLD}" "${RESET}"
  printf '  Choice [U/R/Q]: '
  read -r choice

  choice="$(printf '%s' "$choice" | tr '[:lower:]' '[:upper:]')"
  case "$choice" in
    U)
      info "Upgrading existing installation..."
      SKIP_ENV_GEN=true
      SKIP_PULL=false
      ;;
    R)
      warn "This will DESTROY ALL DATA including the database volumes."
      printf '  Type "yes" to confirm: '
      read -r confirm
      if [ "$confirm" != "yes" ]; then
        die "Reset cancelled."
      fi
      info "Destroying existing installation..."
      docker compose down -v --remove-orphans 2>/dev/null || true
      rm -f "$REPO_ROOT/.env" "$REPO_ROOT/api/.env" "$REPO_ROOT/web/.env"
      SKIP_ENV_GEN=false
      SKIP_PULL=false
      ;;
    Q|*)
      info "Quitting. Run ./install.sh again when ready."
      exit 0
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Step 4 — Interactive Wizard
# ---------------------------------------------------------------------------
prompt_secret() {
  # Read a hidden password field, with confirmation
  local var_name="$1"
  local prompt="$2"
  local value=""
  local confirm_value=""

  while true; do
    printf '  %s%s%s ' "${BOLD}" "$prompt" "${RESET}"
    read -rs value
    printf '\n'
    if [ ${#value} -lt 8 ]; then
      warn "  Password must be at least 8 characters."
      continue
    fi
    printf '  %sConfirm password:%s ' "${BOLD}" "${RESET}"
    read -rs confirm_value
    printf '\n'
    if [ "$value" != "$confirm_value" ]; then
      warn "  Passwords do not match. Try again."
      continue
    fi
    break
  done

  printf -v "$var_name" '%s' "$value"
}

prompt_field() {
  # Read a visible field with an optional default
  local var_name="$1"
  local prompt="$2"
  local default="${3:-}"
  local value=""

  if [ -n "$default" ]; then
    printf '  %s%s%s [%s]: ' "${BOLD}" "$prompt" "${RESET}" "$default"
  else
    printf '  %s%s%s: ' "${BOLD}" "$prompt" "${RESET}"
  fi
  read -r value
  value="${value:-$default}"
  printf -v "$var_name" '%s' "$value"
}

run_wizard() {
  section "Setup wizard"

  # --- Admin account ---
  printf '\n  %s--- Admin Account ---%s\n\n' "${CYAN}" "${RESET}"
  while true; do
    prompt_field admin_email "Email"
    if echo "$admin_email" | grep -qE '^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'; then
      break
    fi
    warn "  Please enter a valid email address."
  done

  prompt_secret admin_password "Password (min 8 chars):"
  prompt_field  admin_name "Full name" "Admin"
  prompt_field  org_name   "Organisation name" "My Organisation"

  # --- LLM Provider ---
  printf '\n  %s--- LLM Provider ---%s\n\n' "${CYAN}" "${RESET}"
  printf '  %s[1]%s OpenAI   %s[2]%s Anthropic   %s[3]%s Skip (configure later)\n\n' \
    "${BOLD}" "${RESET}" "${BOLD}" "${RESET}" "${BOLD}" "${RESET}"
  printf '  Choice [1/2/3]: '
  read -r llm_choice

  case "$llm_choice" in
    1)
      llm_provider="openai"
      prompt_field llm_api_key "OpenAI API key (sk-...)"
      ;;
    2)
      llm_provider="anthropic"
      prompt_field llm_api_key "Anthropic API key (sk-ant-...)"
      ;;
    *)
      llm_provider="skip"
      llm_api_key=""
      info "LLM provider skipped — configure from Settings > LLM Providers after install."
      ;;
  esac

  # --- Slack Bot (optional) ---
  printf '\n  %s--- Slack Bot (optional) ---%s\n\n' "${CYAN}" "${RESET}"
  printf '  Set up a demo Slack bot? [y/N]: '
  read -r setup_slack

  setup_slack_lc="$(printf '%s' "$setup_slack" | tr '[:upper:]' '[:lower:]')"
  if [ "$setup_slack_lc" = "y" ] || [ "$setup_slack_lc" = "yes" ]; then
    prompt_field slack_bot_token "Bot token (xoxb-...)"
    prompt_field slack_app_token "App-level token for Socket Mode (xapp-...) [leave blank for Event Mode]"
    prompt_field slack_channel   "Slack channel name" "general"
    slack_channel="${slack_channel#\#}"  # strip leading #
  fi

  # --- Confirmation ---
  printf '\n'
  section "Confirm setup"
  printf '  Email:        %s\n' "$admin_email"
  printf '  Name:         %s\n' "$admin_name"
  printf '  Organisation: %s\n' "$org_name"
  printf '  LLM:          %s\n' "$llm_provider"
  if [ -n "$slack_bot_token" ]; then
    printf '  Slack bot:    enabled (channel: #%s)\n' "$slack_channel"
  else
    printf '  Slack bot:    skipped\n'
  fi

  printf '\n  %sProceed with installation? [Y/n]%s ' "${BOLD}" "${RESET}"
  read -r proceed
  proceed_lc="$(printf '%s' "$proceed" | tr '[:upper:]' '[:lower:]')"
  case "$proceed_lc" in
    n|no) die "Installation cancelled." ;;
  esac
}

# ---------------------------------------------------------------------------
# Non-interactive mode — read all values from SYNKORA_* env vars
# ---------------------------------------------------------------------------
load_noninteractive() {
  section "Non-interactive mode"

  admin_email="${SYNKORA_ADMIN_EMAIL:-}"
  admin_password="${SYNKORA_ADMIN_PASSWORD:-}"
  admin_name="${SYNKORA_ADMIN_NAME:-Admin}"
  org_name="${SYNKORA_ORG_NAME:-My Organisation}"
  llm_provider="${SYNKORA_LLM_PROVIDER:-skip}"
  llm_api_key="${SYNKORA_LLM_API_KEY:-}"
  slack_bot_token="${SYNKORA_SLACK_BOT_TOKEN:-}"
  slack_app_token="${SYNKORA_SLACK_APP_TOKEN:-}"
  slack_channel="${SYNKORA_SLACK_CHANNEL:-general}"

  [ -z "$admin_email" ]    && die "SYNKORA_ADMIN_EMAIL is required for non-interactive mode"
  [ -z "$admin_password" ] && die "SYNKORA_ADMIN_PASSWORD is required for non-interactive mode"
  [ ${#admin_password} -lt 8 ] && die "SYNKORA_ADMIN_PASSWORD must be at least 8 characters"

  info "Admin email:   $admin_email"
  info "Organisation:  $org_name"
  info "LLM provider:  $llm_provider"
}

# ---------------------------------------------------------------------------
# Step 13 — Start Frontend
# ---------------------------------------------------------------------------
start_frontend() {
  section "Starting frontend"

  if [ "$FRONTEND_MODE" = "docker" ]; then
    info "Starting frontend via Docker..."
    # Uncomment the web service in docker-compose by running a profile
    docker compose \
      --profile web \
      up -d synkora-web 2>/dev/null || {
        warn "Docker frontend not available in compose — try local mode."
        FRONTEND_MODE=local
      }
  fi

  if [ "$FRONTEND_MODE" = "local" ]; then
    if ! check_node >/dev/null 2>&1 || ! check_pnpm >/dev/null 2>&1; then
      warn "Node.js/pnpm not available — skipping frontend start."
      warn "Run manually: cd web && pnpm install && pnpm dev"
      return 0
    fi
    info "Installing frontend dependencies..."
    (cd "$REPO_ROOT/web" && pnpm install --frozen-lockfile --silent)
    info "Starting frontend (background)..."
    (cd "$REPO_ROOT/web" && pnpm dev >/tmp/synkora_web.log 2>&1) &
    WEB_PID=$!
    info "Frontend starting (PID $WEB_PID) — logs: /tmp/synkora_web.log"
    sleep 3
  fi
}

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------
print_summary() {
  local minio_pw="${MINIO_PASSWORD:-minioadmin}"

  printf '\n'
  printf '%s==========================================%s\n' "${GREEN}${BOLD}" "${RESET}"
  printf '%s  Synkora is ready!%s\n' "${GREEN}${BOLD}" "${RESET}"
  printf '%s==========================================%s\n\n' "${GREEN}${BOLD}" "${RESET}"
  printf '  %sWeb App:%s     http://localhost:3005\n'    "${BOLD}" "${RESET}"
  printf '  %sAPI:%s         http://localhost:5001\n'    "${BOLD}" "${RESET}"
  printf '  %sAPI Docs:%s    http://localhost:5001/api/v1/docs\n' "${BOLD}" "${RESET}"
  printf '  %sLangfuse:%s    http://localhost:3001\n'    "${BOLD}" "${RESET}"
  printf '  %sMinIO:%s       http://localhost:9001  (minioadmin / %s)\n' \
    "${BOLD}" "${RESET}" "$minio_pw"
  printf '\n'
  printf '  %sAdmin Login:%s %s\n'  "${BOLD}" "${RESET}" "$admin_email"
  printf '  %sPassword:%s    (as entered)\n' "${BOLD}" "${RESET}"
  printf '\n'
  printf '  %sManagement:%s\n' "${BOLD}" "${RESET}"
  printf '    Stop:      docker compose down\n'
  printf '    Start:     docker compose up -d\n'
  printf '    Logs:      docker compose logs -f api\n'
  printf '    Re-run:    ./install.sh\n'
  printf '\n'
  printf '%s==========================================%s\n\n' "${GREEN}${BOLD}" "${RESET}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  # Parse args
  for arg in "$@"; do
    case "$arg" in
      --non-interactive|-n) NON_INTERACTIVE=true ;;
      --docker-frontend)    FRONTEND_MODE=docker  ;;
      --help|-h)
        printf 'Usage: %s [--non-interactive] [--docker-frontend]\n' "$0"
        printf '\nNon-interactive env vars:\n'
        printf '  SYNKORA_ADMIN_EMAIL, SYNKORA_ADMIN_PASSWORD, SYNKORA_ADMIN_NAME\n'
        printf '  SYNKORA_ORG_NAME, SYNKORA_LLM_PROVIDER, SYNKORA_LLM_API_KEY\n'
        printf '  SYNKORA_SLACK_BOT_TOKEN, SYNKORA_SLACK_APP_TOKEN, SYNKORA_SLACK_CHANNEL\n'
        exit 0
        ;;
    esac
  done

  # Must run from repo root
  [ -f "$REPO_ROOT/docker-compose.yml" ] || \
    die "Must be run from the Synkora repo root (docker-compose.yml not found)"

  # Always operate from repo root so docker compose finds docker-compose.yml
  cd "$REPO_ROOT"

  show_banner

  # Step 1+2: OS detection + prerequisites
  detect_os
  check_resources
  check_prerequisites

  # Step 3: Detect existing install
  SKIP_ENV_GEN=false
  SKIP_PULL=false
  detect_existing_install

  # Step 4: Collect config
  if [ "$NON_INTERACTIVE" = true ]; then
    load_noninteractive
  else
    run_wizard
  fi

  # Step 5: Generate .env files
  if [ "${SKIP_ENV_GEN:-false}" = false ]; then
    generate_env_files
  else
    info "Skipping .env generation (upgrade mode)"
    # Still export POSTGRES_PASSWORD / MINIO_PASSWORD for summary
    POSTGRES_PASSWORD="$(grep '^POSTGRES_PASSWORD=' "$REPO_ROOT/.env" 2>/dev/null | cut -d= -f2 || echo 'synkora')"
    MINIO_PASSWORD="$(grep '^MINIO_ROOT_PASSWORD=' "$REPO_ROOT/.env" 2>/dev/null | cut -d= -f2 || echo 'minioadmin')"
    export POSTGRES_PASSWORD MINIO_PASSWORD
  fi

  # Step 6: Pull images + start services
  if [ "${SKIP_PULL:-false}" = false ]; then
    pull_images
  fi
  start_services

  # Step 7: Wait for postgres + API container
  wait_for_postgres
  wait_for_api_container

  # Step 8: Migrations
  run_migrations

  # Step 9: Seed plans + roles
  seed_plans_and_roles

  # Step 10: Create admin account
  create_admin_account

  # Step 11: Seed template agents
  seed_template_agents

  # Step 12: Optional Slack agent
  seed_slack_agent

  # Step 13: Frontend
  start_frontend

  # Done!
  print_summary
}

main "$@"
