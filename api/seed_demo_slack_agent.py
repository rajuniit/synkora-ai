#!/usr/bin/env python3
"""
Seed a demo Slack bot agent for a freshly installed Synkora instance.

Environment variables:
    SLACK_BOT_TOKEN    (required) - xoxb-* bot token
    SLACK_APP_TOKEN    (optional) - xapp-* app-level token for Socket Mode
    SLACK_CHANNEL_NAME (optional) - Channel name to note in config, default "general"
    ADMIN_EMAIL        (required) - Email of the existing super admin account

The script creates:
  1. An Agent record (type=LLM, general-purpose assistant)
  2. A SlackBot record with encrypted tokens
  3. An AgentOutputConfig pointing to the Slack channel

Safe to re-run: skips creation if an agent named "Demo Assistant" already
exists for this account's tenant.
"""

import os
import sys
import uuid

# PYTHONPATH=/app/api is set in Dockerfile.dev; no path manipulation needed.
from src.core.database import get_db
from src.models import Account, Agent, AgentOutputConfig, OutputProvider
from src.models.slack_bot import SlackBot
from src.services.agents.security import encrypt_value

_SYSTEM_PROMPT = """You are a helpful assistant connected to this Slack workspace.
Answer questions clearly and concisely. When you don't know something, say so.
You can help with: answering questions, summarising topics, drafting messages,
and general productivity tasks."""

_LLM_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1024,
}


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"[x] Environment variable {name} is required but not set.", flush=True)
        sys.exit(1)
    return val


def main() -> None:
    slack_bot_token = _require_env("SLACK_BOT_TOKEN")
    slack_app_token = os.environ.get("SLACK_APP_TOKEN", "").strip()
    channel_name = os.environ.get("SLACK_CHANNEL_NAME", "general").lstrip("#")
    admin_email = _require_env("ADMIN_EMAIL")

    db = next(get_db())
    try:
        # 1. Resolve the admin account and tenant
        account = db.query(Account).filter(Account.email == admin_email).first()
        if not account:
            print(f"[x] No account found for email: {admin_email}", flush=True)
            sys.exit(1)

        from src.models import TenantAccountJoin

        taj = db.query(TenantAccountJoin).filter(TenantAccountJoin.account_id == account.id).first()
        if not taj:
            print("[x] Admin account has no tenant association.", flush=True)
            sys.exit(1)

        tenant_id = taj.tenant_id
        print(f"[*] Using tenant: {tenant_id}", flush=True)

        # 2. Check for existing demo agent
        existing = db.query(Agent).filter(Agent.agent_name == "Demo Assistant", Agent.tenant_id == tenant_id).first()
        if existing:
            print("[!] Demo Assistant agent already exists — skipping.", flush=True)
            sys.exit(0)

        # 3. Create Agent
        agent = Agent(
            id=uuid.uuid4(),
            agent_name="Demo Assistant",
            agent_type="LLM",
            description="General-purpose assistant connected to Slack.",
            system_prompt=_SYSTEM_PROMPT,
            llm_config=_LLM_CONFIG,
            tools_config={"enabled_tools": ["slack_tools"]},
            tenant_id=tenant_id,
            status="active",
        )
        db.add(agent)
        db.flush()
        print(f"[+] Created agent: {agent.id}", flush=True)

        # 4. Encrypt tokens
        enc_bot_token = encrypt_value(slack_bot_token)
        enc_app_token = encrypt_value(slack_app_token) if slack_app_token else None

        # 5. Create SlackBot
        slack_bot = SlackBot(
            id=uuid.uuid4(),
            agent_id=agent.id,
            tenant_id=tenant_id,
            bot_name="Demo Assistant",
            slack_app_id="unknown",  # will be updated on first connect
            slack_bot_token=enc_bot_token,
            slack_app_token=enc_app_token,
            connection_mode="socket" if slack_app_token else "event",
            is_active=True,
            connection_status="disconnected",
            created_by=account.id,
        )
        db.add(slack_bot)
        db.flush()
        print(f"[+] Created SlackBot: {slack_bot.id}", flush=True)

        # 6. Create AgentOutputConfig
        output_config = AgentOutputConfig(
            id=uuid.uuid4(),
            agent_id=agent.id,
            slack_bot_id=slack_bot.id,
            tenant_id=tenant_id,
            provider=OutputProvider.SLACK,
            name=f"#{channel_name}",
            description=f"Routes agent responses to #{channel_name}",
            config={"channel_name": channel_name},
            is_enabled=True,
            send_on_webhook_trigger=True,
            send_on_chat_completion=False,
        )
        db.add(output_config)
        db.commit()

        print("[+] Demo Slack agent created successfully!", flush=True)
        print("", flush=True)
        print("Next steps:", flush=True)
        print(f"  1. Invite your bot to #{channel_name} in Slack: /invite @Demo Assistant", flush=True)
        print("  2. Open the Synkora dashboard and start the bot worker", flush=True)
        print("  3. Send a message to the bot in Slack to test it", flush=True)

    except Exception as exc:
        db.rollback()
        import traceback

        traceback.print_exc()
        print(f"[x] Error: {exc}", flush=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
