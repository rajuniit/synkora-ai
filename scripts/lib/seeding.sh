#!/usr/bin/env bash
# Database migration and seeding helpers.
# Requires colors.sh, spinner.sh, and docker_utils.sh to be sourced first.

# ---------------------------------------------------------------------------
# Run Alembic migrations
# ---------------------------------------------------------------------------
run_migrations() {
  section "Running database migrations"
  spinner_start "Applying migrations..."

  if api_exec alembic upgrade head 2>/tmp/synkora_migrations.log; then
    spinner_stop_ok "Migrations applied"
  else
    spinner_stop_fail "Migration failed"
    error "Migration output:"
    cat /tmp/synkora_migrations.log >&2
    die "Migrations failed. Fix the errors above and re-run ./install.sh"
  fi
}

# ---------------------------------------------------------------------------
# Seed roles, permissions, and subscription plans
# ---------------------------------------------------------------------------
seed_plans_and_roles() {
  section "Seeding plans and roles"
  spinner_start "Seeding subscription plans and roles..."

  if api_exec python -c "
import asyncio
from src.core.database import get_async_session_factory
from src.services.billing.seed_plans import seed_subscription_plans
from src.services.permissions.seed_roles_permissions import seed_roles_and_permissions

async def main():
    factory = get_async_session_factory()
    async with factory() as db:
        await seed_roles_and_permissions(db)
        await seed_subscription_plans(db)

asyncio.run(main())
" 2>/tmp/synkora_seed_plans.log; then
    spinner_stop_ok "Plans and roles seeded"
  else
    spinner_stop_fail "Seeding failed"
    error "Seed output:"
    cat /tmp/synkora_seed_plans.log >&2
    die "Seeding failed. See errors above."
  fi
}

# ---------------------------------------------------------------------------
# Create admin account (non-interactive)
# ---------------------------------------------------------------------------
create_admin_account() {
  section "Creating admin account"
  spinner_start "Creating super admin: ${admin_email}..."

  if docker compose exec -T \
      -e ADMIN_EMAIL="$admin_email" \
      -e ADMIN_PASSWORD="$admin_password" \
      -e ADMIN_NAME="$admin_name" \
      -e TENANT_NAME="$org_name" \
      api python setup_noninteractive.py >/tmp/synkora_create_admin.log 2>&1; then
    spinner_stop_ok "Admin account created"
  else
    # Check if it failed because account already exists (stdout captured above)
    if grep -q "already exists" /tmp/synkora_create_admin.log 2>/dev/null; then
      spinner_stop
      warn "Admin account already exists — skipping"
    else
      spinner_stop_fail "Admin creation failed"
      error "Output:"
      cat /tmp/synkora_create_admin.log >&2
      die "Failed to create admin account."
    fi
  fi
}

# ---------------------------------------------------------------------------
# Seed template agents
# ---------------------------------------------------------------------------
seed_template_agents() {
  section "Seeding template agents"
  spinner_start "Creating template agents..."

  if api_exec python -c "
import asyncio
from src.core.database import get_async_session_factory
from src.services.agents.seed_template_agents import seed_template_agents

async def main():
    factory = get_async_session_factory()
    async with factory() as db:
        await seed_template_agents(db)

asyncio.run(main())
" 2>/tmp/synkora_seed_agents.log; then
    spinner_stop_ok "Template agents seeded"
  else
    spinner_stop
    warn "Template agent seeding had warnings (non-fatal):"
    tail -5 /tmp/synkora_seed_agents.log >&2 || true
  fi
}

# ---------------------------------------------------------------------------
# Seed demo Slack agent (optional)
# ---------------------------------------------------------------------------
seed_slack_agent() {
  [ -z "$slack_bot_token" ] && return 0

  section "Creating demo Slack agent"
  spinner_start "Setting up Slack bot..."

  if docker compose exec -T \
      -e SLACK_BOT_TOKEN="$slack_bot_token" \
      -e SLACK_APP_TOKEN="$slack_app_token" \
      -e SLACK_CHANNEL_NAME="$slack_channel" \
      -e ADMIN_EMAIL="$admin_email" \
      api python seed_demo_slack_agent.py 2>/tmp/synkora_slack.log; then
    spinner_stop_ok "Demo Slack agent created"
  else
    spinner_stop
    warn "Slack agent setup had errors (non-fatal):"
    tail -10 /tmp/synkora_slack.log >&2 || true
    warn "You can set up Slack manually from the dashboard later."
  fi
}
