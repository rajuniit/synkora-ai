#!/usr/bin/env bash
# Terminal color helpers — tput-based with plain-text fallback.
# Source this file; do not execute it directly.

# Detect color support
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1; then
  _COLORS=1
else
  _COLORS=0
fi

_tput() {
  [ "$_COLORS" -eq 1 ] && tput "$@" 2>/dev/null || true
}

# Attributes
BOLD="$(_tput bold)"
RESET="$(_tput sgr0)"

# Colors
RED="$(_tput setaf 1)"
GREEN="$(_tput setaf 2)"
YELLOW="$(_tput setaf 3)"
BLUE="$(_tput setaf 4)"
CYAN="$(_tput setaf 6)"

# Formatted output helpers
info()    { printf '%s[*]%s %s\n' "${CYAN}${BOLD}"   "${RESET}" "$*"; }
success() { printf '%s[+]%s %s\n' "${GREEN}${BOLD}"  "${RESET}" "$*"; }
warn()    { printf '%s[!]%s %s\n' "${YELLOW}${BOLD}" "${RESET}" "$*"; }
error()   { printf '%s[x]%s %s\n' "${RED}${BOLD}"    "${RESET}" "$*" >&2; }

die() {
  error "$*"
  exit 1
}

# Section header
section() {
  printf '\n%s=== %s ===%s\n' "${BLUE}${BOLD}" "$*" "${RESET}"
}

# Check/cross symbols
check() { printf '  %s[+]%s %s\n' "${GREEN}" "${RESET}" "$*"; }
cross() { printf '  %s[x]%s %s\n' "${RED}"   "${RESET}" "$*"; }
