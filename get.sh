#!/usr/bin/env bash
# =============================================================================
# Synkora Bootstrap — one-line installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/getsynkora/synkora-ai/main/get.sh | bash
#
#   # Custom install directory
#   curl -fsSL https://raw.githubusercontent.com/getsynkora/synkora-ai/main/get.sh | \
#     SYNKORA_INSTALL_DIR=~/my-synkora bash
#
#   # Non-interactive (CI/CD)
#   curl -fsSL https://raw.githubusercontent.com/getsynkora/synkora-ai/main/get.sh | \
#     SYNKORA_ADMIN_EMAIL=admin@example.com \
#     SYNKORA_ADMIN_PASSWORD=securepass123 \
#     bash -s -- --non-interactive
#
# This script clones (or updates) the Synkora repository and runs install.sh.
# =============================================================================
set -euo pipefail

REPO_URL="https://github.com/getsynkora/synkora-ai.git"
INSTALL_DIR="${SYNKORA_INSTALL_DIR:-${HOME}/synkora-ai}"

# ---------------------------------------------------------------------------
# Minimal print helpers (no deps — this script runs before lib/ is available)
# ---------------------------------------------------------------------------
_bold=""
_reset=""
_cyan=""
_green=""
_yellow=""
_red=""

if [ -t 1 ] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1; then
  _bold="$(tput bold)"
  _reset="$(tput sgr0)"
  _cyan="$(tput setaf 6)"
  _green="$(tput setaf 2)"
  _yellow="$(tput setaf 3)"
  _red="$(tput setaf 1)"
fi

info()    { printf '%s[*]%s %s\n' "${_cyan}${_bold}"   "${_reset}" "$*"; }
success() { printf '%s[+]%s %s\n' "${_green}${_bold}"  "${_reset}" "$*"; }
warn()    { printf '%s[!]%s %s\n' "${_yellow}${_bold}" "${_reset}" "$*"; }
die()     { printf '%s[x]%s %s\n' "${_red}${_bold}"    "${_reset}" "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
printf '\n'
printf '%s' "${_bold}${_cyan}"
cat <<'BANNER'
  ███████╗██╗   ██╗███╗   ██╗██╗  ██╗ ██████╗ ██████╗  █████╗
  ██╔════╝╚██╗ ██╔╝████╗  ██║██║ ██╔╝██╔═══██╗██╔══██╗██╔══██╗
  ███████╗ ╚████╔╝ ██╔██╗ ██║█████╔╝ ██║   ██║██████╔╝███████║
  ╚════██║  ╚██╔╝  ██║╚██╗██║██╔═██╗ ██║   ██║██╔══██╗██╔══██║
  ███████║   ██║   ██║ ╚████║██║  ██╗╚██████╔╝██║  ██║██║  ██║
  ╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
BANNER
printf '%s' "${_reset}"
printf '\n  %sAI Agent Platform%s  •  One-line installer\n\n' "${_bold}" "${_reset}"

# ---------------------------------------------------------------------------
# Check for git
# ---------------------------------------------------------------------------
if ! command -v git >/dev/null 2>&1; then
  die "git is required but not installed.

  Install it first:
    macOS:   brew install git
    Ubuntu:  sudo apt-get install -y git
    Fedora:  sudo dnf install -y git
  Then re-run the installer."
fi

# ---------------------------------------------------------------------------
# Clone or update the repo
# ---------------------------------------------------------------------------
if [ -d "$INSTALL_DIR/.git" ]; then
  info "Found existing installation at ${INSTALL_DIR} — pulling latest changes..."
  git -C "$INSTALL_DIR" pull --ff-only || {
    warn "git pull failed (you may have local changes). Continuing with existing code."
  }
  success "Repository up to date"
else
  if [ -e "$INSTALL_DIR" ]; then
    die "Path '${INSTALL_DIR}' exists but is not a git repository.
  Move or remove it, or set a different location:
    SYNKORA_INSTALL_DIR=~/my-synkora bash"
  fi

  info "Cloning Synkora into ${INSTALL_DIR} ..."
  git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
  success "Repository cloned"
fi

# ---------------------------------------------------------------------------
# Hand off to install.sh
# ---------------------------------------------------------------------------
cd "$INSTALL_DIR"

if [ ! -x "./install.sh" ]; then
  chmod +x ./install.sh
fi

printf '\n'
info "Starting Synkora installer from ${INSTALL_DIR} ..."
printf '\n'

exec ./install.sh "$@"
