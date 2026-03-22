#!/usr/bin/env python3
"""
Script to add LLM configuration to existing Agent Builder Assistant.

Usage:
    docker-compose exec api python update_builder_assistant_llm_config.py
"""

import os
import sys
from uuid import UUID, uuid4

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models import Agent, AgentLLMConfig


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("UPDATE BUILDER ASSISTANT LLM CONFIG")
    print("=" * 60)

    db: Session = next(get_db())

    try:
        # Platform tenant ID
        platform_tenant_id = UUID("00000000-0000-0000-0000-000000000000")

        # Find the agent
        agent = (
            db.query(Agent)
            .filter(Agent.agent_name == "agent_builder_assistant", Agent.tenant_id == platform_tenant_id)
            .first()
        )

        if not agent:
            print("❌ Agent Builder Assistant not found!")
            sys.exit(1)

        print(f"✅ Found agent: {agent.id}")

        # Check if LLM config already exists
        existing_config = (
            db.query(AgentLLMConfig)
            .filter(AgentLLMConfig.agent_id == agent.id, AgentLLMConfig.is_default.is_(True))
            .first()
        )

        if existing_config:
            print(f"✅ Default LLM config already exists: {existing_config.id}")
            sys.exit(0)

        # Create default LLM configuration
        llm_config = AgentLLMConfig(
            id=uuid4(),
            agent_id=agent.id,
            tenant_id=platform_tenant_id,
            name="Default Configuration",
            provider="google",
            model_name="gemini-2.0-flash-exp",
            api_key="",  # Will use platform API key
            temperature=0.7,
            max_tokens=4096,
            top_p=1.0,
            is_default=True,
            display_order=0,
            enabled=True,
        )

        db.add(llm_config)
        db.commit()

        print(f"✅ Created default LLM config: {llm_config.id}")
        print("\n" + "=" * 60)
        print("UPDATE COMPLETE")
        print("=" * 60)
        sys.exit(0)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
