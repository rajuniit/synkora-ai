#!/usr/bin/env python3
"""
Script to seed the Agent Builder Assistant.

This is a platform-level agent that helps users create and configure other agents.
It's only available to paid users and cannot be deleted or modified.

Usage:
    python seed_agent_builder_assistant.py
"""

import os
import sys
from uuid import UUID, uuid4

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models import Agent, AgentLLMConfig, Tenant, TenantPlan, TenantStatus, TenantType

# Comprehensive system prompt for the builder assistant
BUILDER_ASSISTANT_SYSTEM_PROMPT = """You are the Agent Builder Assistant for Synkora - an expert AI system that helps users create, configure, and optimize AI agents.

**Your Responsibilities:**

1. CONTENT GENERATION
   - Generate system prompts tailored to specific use cases
   - Create compelling agent names and descriptions
   - Format suggestion prompts in proper JSON array format
   - Generate configuration templates

2. TOOL RECOMMENDATIONS
   - Analyze requirements and suggest appropriate tools
   - Explain tool capabilities and use cases
   - Recommend tool combinations for complex workflows
   - Available tools: web_search, gmail_tools, slack_tools, github_tools, google_drive_tools, google_calendar_tools, zoom_tools, storage_tools, file_tools, command_tools, database_tools, elasticsearch_tools, contract_analysis_tools

3. CONFIGURATION GUIDANCE
   - Recommend optimal LLM settings (temperature, max_tokens, top_p)
   - Guide model selection based on requirements and budget
   - Suggest provider-specific optimizations

4. BEST PRACTICES
   - Security recommendations
   - Performance optimization
   - Cost efficiency
   - User experience tips

**Response Format:**
Provide clear, copy-ready content with brief explanations.

Always be helpful, concise, and provide actionable suggestions."""


def create_builder_assistant(tenant_id: UUID, db: Session) -> tuple[bool, str, str]:
    """
    Create the Agent Builder Assistant.

    Args:
        tenant_id: Platform tenant ID
        db: Database session

    Returns:
        Tuple of (success: bool, message: str, agent_id: str)
    """
    try:
        # Check if assistant already exists
        existing = (
            db.query(Agent).filter(Agent.agent_name == "agent_builder_assistant", Agent.tenant_id == tenant_id).first()
        )

        if existing:
            return True, "Agent Builder Assistant already exists", str(existing.id)

        # Create the assistant agent
        agent = Agent(
            id=uuid4(),
            tenant_id=tenant_id,
            agent_name="agent_builder_assistant",
            agent_type="LLM",
            description="Expert AI assistant that helps you create and configure AI agents. Get recommendations for system prompts, tool selection, LLM settings, and best practices.",
            avatar=None,
            system_prompt=BUILDER_ASSISTANT_SYSTEM_PROMPT,
            llm_config={
                "provider": "google",
                "model_name": "gemini-2.0-flash-exp",
                "temperature": 0.7,
                "max_tokens": 4096,
                "top_p": 1.0,
                "api_key": "",
            },
            tools_config=None,
            agent_metadata={
                "is_platform_agent": True,
                "available_to": "paid_users",
                "purpose": "agent_creation_assistance",
                "version": "1.0.0",
            },
            status="ACTIVE",
            suggestion_prompts=[
                {
                    "title": "Generate System Prompt",
                    "description": "Create a tailored system prompt for your agent",
                    "prompt": "Help me generate a system prompt for a [type] agent that [purpose]",
                    "icon": "✍️",
                },
                {
                    "title": "Recommend Tools",
                    "description": "Get tool suggestions based on your use case",
                    "prompt": "Which tools should I enable for [use case]?",
                    "icon": "🔧",
                },
                {
                    "title": "Optimize Configuration",
                    "description": "Get recommendations for LLM settings",
                    "prompt": "What LLM settings should I use for [task type]?",
                    "icon": "⚙️",
                },
                {
                    "title": "Format JSON",
                    "description": "Help with JSON formatting for configs",
                    "prompt": "Help me format suggestion prompts in JSON for [use case]",
                    "icon": "📋",
                },
                {
                    "title": "Best Practices",
                    "description": "Learn best practices for your agent",
                    "prompt": "What are best practices for creating a [type] agent?",
                    "icon": "⭐",
                },
            ],
            is_public=False,
            category="Platform",
            tags=["assistant", "helper", "platform", "agent-creation"],
            execution_count=0,
            success_count=0,
        )

        db.add(agent)
        db.flush()  # Flush to get the agent ID

        # Create default LLM configuration
        llm_config = AgentLLMConfig(
            id=uuid4(),
            agent_id=agent.id,
            tenant_id=tenant_id,
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
        db.refresh(agent)

        return True, "Agent Builder Assistant created successfully", str(agent.id)

    except Exception as e:
        db.rollback()
        import traceback

        traceback.print_exc()
        return False, f"Error creating builder assistant: {str(e)}", ""


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("SYNKORA - AGENT BUILDER ASSISTANT SETUP")
    print("=" * 60)
    print("\nThis script will create the Agent Builder Assistant.")
    print("This is a platform-level agent that helps users create agents.\n")

    db: Session = next(get_db())

    try:
        # Platform tenant ID (all zeros for platform)
        platform_tenant_id = UUID("00000000-0000-0000-0000-000000000000")

        print("📋 Step 1: Checking platform tenant...")
        # Check if platform tenant exists
        platform_tenant = db.query(Tenant).filter(Tenant.id == platform_tenant_id).first()

        if not platform_tenant:
            print("   Creating platform tenant...")
            platform_tenant = Tenant(
                id=platform_tenant_id,
                name="Platform",
                plan=TenantPlan.ENTERPRISE,
                status=TenantStatus.ACTIVE,
                tenant_type=TenantType.PLATFORM,
            )
            db.add(platform_tenant)
            db.commit()
            print("   ✅ Platform tenant created")
        else:
            print("   ✅ Platform tenant found")

        print("\n📋 Step 2: Creating Agent Builder Assistant...")
        # Create the builder assistant
        success, message, agent_id = create_builder_assistant(tenant_id=platform_tenant_id, db=db)

        if success:
            print(f"   ✅ {message}")
            print("\n" + "=" * 60)
            print("AGENT BUILDER ASSISTANT SETUP COMPLETE")
            print("=" * 60)
            print(f"Agent ID:     {agent_id}")
            print("Agent Name:   agent_builder_assistant")
            print("Status:       ACTIVE")
            print("LLM Config:   Default configuration created")
            print("Available to: Paid users only")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Configure platform API key in .env or platform settings")
            print("2. Test the assistant in the agent creation flow")
            print("3. Verify streaming responses work correctly")
            print("=" * 60)
            sys.exit(0)
        else:
            print(f"   ❌ {message}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
