#!/usr/bin/env bash
# Background spinner with PID management.
# Requires colors.sh to be sourced first.

_SPINNER_PID=""
_SPINNER_MSG=""

_spinner_loop() {
  # ASCII-only frames — safe on all locales and BSD/GNU cut implementations
  local frames=$'|/-\\'
  local len=4
  local i=0
  while true; do
    i=$(( (i + 1) % len ))
    char=$(printf '%s' "$frames" | cut -c$((i+1)))
    printf '\r  %s%s%s %s  ' "${CYAN}" "$char" "${RESET}" "$_SPINNER_MSG"
    sleep 0.1
  done
}

spinner_start() {
  _SPINNER_MSG="$*"
  if [ -t 1 ]; then
    tput civis 2>/dev/null || true   # hide cursor
    _spinner_loop &
    _SPINNER_PID=$!
  else
    info "$*"
  fi
}

spinner_stop() {
  if [ -n "$_SPINNER_PID" ]; then
    kill "$_SPINNER_PID" 2>/dev/null || true
    wait "$_SPINNER_PID" 2>/dev/null || true
    _SPINNER_PID=""
    tput cnorm 2>/dev/null || true   # restore cursor
    printf '\r%s\n' "$(printf '%*s' "$(tput cols 2>/dev/null || echo 80)" '')"
    printf '\r'
  fi
}

spinner_stop_ok() {
  spinner_stop
  success "$*"
}

spinner_stop_fail() {
  spinner_stop
  error "$*"
}

# Trap to ensure spinner is killed on exit
trap 'spinner_stop' EXIT INT TERM
