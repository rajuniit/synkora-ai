"""
Ghostwriter Agent implementation.

Provides an AI agent that drafts content in the voice/style of specific people
by analyzing their past communications and emulating their writing patterns.
"""

import logging
import time
from typing import Any
from uuid import UUID

from google import genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.ghostwriter_draft import GhostwriterDraft
from src.models.writing_style_profile import WritingStyleProfile
from src.services.agents.base_agent import BaseAgent
from src.services.agents.config import AgentConfig
from src.services.ghostwriter.writing_style_analyzer import WritingStyleAnalyzer
from src.services.knowledge_base.rag_service import RAGService

logger = logging.getLogger(__name__)


class GhostwriterAgent(BaseAgent):
    """
    Ghostwriter agent that drafts content in specific writing styles.

    This agent analyzes past communications to understand writing patterns,
    retrieves relevant context from knowledge bases, and generates drafts
    that match the target person's voice and style.
    """

    def __init__(
        self,
        config: AgentConfig,
        agent_model: Agent,
        db_session: AsyncSession,
        google_client: genai.Client,
    ):
        """
        Initialize Ghostwriter agent.

        Args:
            config: Agent configuration
            agent_model: Database agent model
            db_session: Database session
            google_client: Google GenAI client
        """
        super().__init__(config)
        self.agent_model = agent_model
        self.db_session = db_session
        self.rag_service = RAGService(db_session, google_client)
        self.style_analyzer = WritingStyleAnalyzer(db_session)

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the Ghostwriter agent to generate a draft.

        Args:
            input_data: Dictionary containing:
                - person_identifier: Email or ID of person to emulate (required)
                - topic: What to write about (required)
                - content_type: Type of content (email, brief, proposal, etc.)
                - purpose: Purpose of the communication
                - additional_context: Extra context to include
                - tone_adjustment: Adjust tone (more_formal, more_casual, etc.)
                - temperature: Optional temperature override
                - max_tokens: Optional max tokens override
                - save_draft: Whether to save the draft (default: True)

        Returns:
            Dictionary containing:
                - draft: The generated draft content
                - person_identifier: Person being emulated
                - style_profile_id: ID of style profile used
                - confidence_score: Confidence in style matching
                - sources: List of sources used for context
                - draft_id: ID of saved draft (if save_draft=True)
                - model: Model used
                - provider: Provider used
                - generation_time_ms: Time taken to generate
        """
        if not self.llm_client:
            raise RuntimeError("Client not initialized. Call initialize_client() first.")

        # Validate required inputs
        person_identifier = input_data.get("person_identifier")
        topic = input_data.get("topic")

        if not person_identifier:
            raise ValueError("'person_identifier' is required")
        if not topic:
            raise ValueError("'topic' is required")

        # Extract optional parameters
        content_type = input_data.get("content_type", "email")
        purpose = input_data.get("purpose")
        additional_context = input_data.get("additional_context", "")
        tone_adjustment = input_data.get("tone_adjustment")
        temperature = input_data.get("temperature", self.config.llm_config.temperature)
        max_tokens = input_data.get("max_tokens", self.config.llm_config.max_tokens)
        save_draft = input_data.get("save_draft", True)

        start_time = time.time()

        try:
            # Step 1: Get or create style profile
            logger.info(f"Retrieving style profile for: {person_identifier}")
            style_profile = await self._get_style_profile(person_identifier)

            if not style_profile:
                raise ValueError(
                    f"No style profile found for {person_identifier}. Please analyze writing samples first."
                )

            # Step 2: Retrieve relevant context from knowledge bases
            logger.info("Retrieving relevant context from knowledge bases")
            context_result = await self._retrieve_context(topic, person_identifier)

            # Step 3: Generate draft with style constraints
            logger.info("Generating draft with style emulation")
            draft_content = await self._generate_draft(
                person_identifier=person_identifier,
                style_profile=style_profile,
                topic=topic,
                content_type=content_type,
                purpose=purpose,
                additional_context=additional_context,
                retrieved_context=context_result["context"],
                tone_adjustment=tone_adjustment,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            generation_time_ms = int((time.time() - start_time) * 1000)

            # Step 4: Save draft if requested
            draft_id = None
            if save_draft:
                draft_id = await self._save_draft(
                    person_identifier=person_identifier,
                    style_profile=style_profile,
                    topic=topic,
                    content_type=content_type,
                    purpose=purpose,
                    additional_context=additional_context,
                    tone_adjustment=tone_adjustment,
                    draft_content=draft_content,
                    sources=context_result["sources"],
                    generation_time_ms=generation_time_ms,
                )

            logger.info(
                f"Ghostwriter draft generated successfully in {generation_time_ms}ms "
                f"(confidence: {style_profile.confidence_score:.2f})"
            )

            return {
                "draft": draft_content,
                "person_identifier": person_identifier,
                "style_profile_id": str(style_profile.id),
                "confidence_score": style_profile.confidence_score,
                "sources": context_result["sources"],
                "num_sources": context_result["num_sources"],
                "draft_id": str(draft_id) if draft_id else None,
                "model": self.config.llm_config.model_name,
                "provider": self.config.llm_config.provider,
                "generation_time_ms": generation_time_ms,
                "content_type": content_type,
            }

        except Exception as e:
            logger.error(f"Ghostwriter agent execution failed: {e}", exc_info=True)
            raise

    async def _get_style_profile(self, person_identifier: str) -> WritingStyleProfile | None:
        """
        Get style profile for a person.

        Args:
            person_identifier: Email or ID of the person

        Returns:
            WritingStyleProfile or None
        """
        stmt = select(WritingStyleProfile).where(
            WritingStyleProfile.tenant_id == self.agent_model.tenant_id,
            WritingStyleProfile.person_identifier == person_identifier,
        )
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def _retrieve_context(self, topic: str, person_identifier: str) -> dict[str, Any]:
        """
        Retrieve relevant context from knowledge bases.

        Args:
            topic: Topic to search for
            person_identifier: Person identifier for filtering

        Returns:
            Dictionary with context and sources
        """
        # Check if agent has knowledge bases
        if not self.agent_model.knowledge_bases:
            return {"context": "", "sources": [], "num_sources": 0}

        # Build search query
        query = f"Communications from {person_identifier} about: {topic}"

        # Retrieve context using RAG service
        rag_result = await self.rag_service.augment_prompt_with_context(
            query=query,
            agent=self.agent_model,
            system_prompt="",
            max_context_tokens=2000,  # Limit context to leave room for style instructions
        )

        return {
            "context": rag_result["context"],
            "sources": rag_result["sources"],
            "num_sources": rag_result["num_sources"],
        }

    async def _generate_draft(
        self,
        person_identifier: str,
        style_profile: WritingStyleProfile,
        topic: str,
        content_type: str,
        purpose: str | None,
        additional_context: str,
        retrieved_context: str,
        tone_adjustment: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Generate draft with style emulation.

        Args:
            person_identifier: Person to emulate
            style_profile: Style profile to use
            topic: Topic to write about
            content_type: Type of content
            purpose: Purpose of communication
            additional_context: Additional context
            retrieved_context: Context from RAG
            tone_adjustment: Tone adjustment
            temperature: LLM temperature
            max_tokens: Max tokens

        Returns:
            Generated draft content
        """
        # Build style instructions from profile
        style_instructions = self._build_style_instructions(style_profile, tone_adjustment)

        # Build the prompt
        prompt_parts = [
            f"You are ghostwriting a {content_type} in the voice of {person_identifier}.",
            "",
            "WRITING STYLE TO EMULATE:",
            style_instructions,
            "",
        ]

        if retrieved_context:
            prompt_parts.extend(
                [
                    "RELEVANT CONTEXT:",
                    retrieved_context,
                    "",
                ]
            )

        if additional_context:
            prompt_parts.extend(
                [
                    "ADDITIONAL CONTEXT:",
                    additional_context,
                    "",
                ]
            )

        prompt_parts.extend(
            [
                f"TOPIC: {topic}",
                "",
            ]
        )

        if purpose:
            prompt_parts.extend(
                [
                    f"PURPOSE: {purpose}",
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "INSTRUCTIONS:",
                f"Write a {content_type} that:",
                "1. Matches the writing style characteristics described above",
                "2. Addresses the topic comprehensively",
                "3. Uses the person's typical tone, vocabulary, and communication patterns",
                "4. Incorporates relevant context where appropriate",
                "5. Maintains the person's characteristic opening and closing styles",
                "",
                f"Generate the {content_type} now:",
            ]
        )

        full_prompt = "\n".join(prompt_parts)

        # Generate using LLM
        draft = await self.llm_client.generate_content(
            prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return draft.strip()

    def _build_style_instructions(self, style_profile: WritingStyleProfile, tone_adjustment: str | None) -> str:
        """
        Build style instructions from profile.

        Args:
            style_profile: Style profile
            tone_adjustment: Optional tone adjustment

        Returns:
            Style instructions text
        """
        tone = style_profile.tone_characteristics
        vocab = style_profile.vocabulary_patterns
        sentence = style_profile.sentence_metrics
        comm = style_profile.communication_patterns

        instructions = []

        # Tone
        instructions.append(f"- Tone: {self._describe_tone(tone, tone_adjustment)}")

        # Vocabulary
        if vocab.get("common_phrases"):
            phrases = ", ".join(vocab["common_phrases"][:5])
            instructions.append(f"- Common phrases: {phrases}")

        # Sentence structure
        instructions.append(
            f"- Sentence length: Average {sentence.get('avg_sentence_length', 15)} words, "
            f"{sentence.get('paragraph_style', 'medium')} paragraphs"
        )

        if sentence.get("bullet_point_usage", 0) > 0.3:
            instructions.append("- Frequently uses bullet points and lists")

        # Communication patterns
        opening = comm.get("opening_style", "direct")
        closing = comm.get("closing_style", "simple")
        instructions.append(f"- Opening style: {opening}")
        instructions.append(f"- Closing style: {closing}")

        if vocab.get("greeting_patterns"):
            greetings = vocab["greeting_patterns"][:2]
            instructions.append(f"- Typical greetings: {', '.join(greetings)}")

        if vocab.get("closing_patterns"):
            closings = vocab["closing_patterns"][:2]
            instructions.append(f"- Typical closings: {', '.join(closings)}")

        return "\n".join(instructions)

    def _describe_tone(self, tone_chars: dict, tone_adjustment: str | None) -> str:
        """
        Describe tone characteristics.

        Args:
            tone_chars: Tone characteristics
            tone_adjustment: Optional adjustment

        Returns:
            Tone description
        """
        formal = tone_chars.get("formal_score", 0.5)
        professional = tone_chars.get("professional_score", 0.5)
        friendly = tone_chars.get("friendly_score", 0.5)
        enthusiasm = tone_chars.get("enthusiasm_level", 0.5)

        # Apply tone adjustment
        if tone_adjustment == "more_formal":
            formal = min(formal + 0.2, 1.0)
            professional = min(professional + 0.2, 1.0)
        elif tone_adjustment == "more_casual":
            formal = max(formal - 0.2, 0.0)
            friendly = min(friendly + 0.2, 1.0)

        # Build description
        parts = []

        if formal > 0.6:
            parts.append("formal")
        elif formal < 0.4:
            parts.append("casual")

        if professional > 0.7:
            parts.append("professional")

        if friendly > 0.6:
            parts.append("friendly")

        if enthusiasm > 0.6:
            parts.append("enthusiastic")

        return ", ".join(parts) if parts else "balanced"

    async def _save_draft(
        self,
        person_identifier: str,
        style_profile: WritingStyleProfile,
        topic: str,
        content_type: str,
        purpose: str | None,
        additional_context: str,
        tone_adjustment: str | None,
        draft_content: str,
        sources: list,
        generation_time_ms: int,
    ) -> UUID:
        """
        Save draft to database.

        Args:
            person_identifier: Person identifier
            style_profile: Style profile used
            topic: Topic
            content_type: Content type
            purpose: Purpose
            additional_context: Additional context
            tone_adjustment: Tone adjustment
            draft_content: Generated draft
            sources: Sources used
            generation_time_ms: Generation time

        Returns:
            Draft ID
        """
        draft = GhostwriterDraft(
            tenant_id=self.agent_model.tenant_id,
            agent_id=self.agent_model.id,
            content_type=content_type,
            person_identifier=person_identifier,
            topic=topic,
            purpose=purpose,
            additional_context=additional_context,
            tone_adjustment=tone_adjustment,
            draft_content=draft_content,
            style_profile_id=style_profile.id,
            sources_used=sources,
            confidence_score=style_profile.confidence_score,
            generation_time_ms=generation_time_ms,
            model_used=self.config.llm_config.model_name,
            provider_used=self.config.llm_config.provider,
        )

        self.db_session.add(draft)
        await self.db_session.commit()
        await self.db_session.refresh(draft)

        logger.info(f"Draft saved with ID: {draft.id}")
        return draft.id

    def cleanup(self) -> None:
        """Cleanup agent resources."""
        if self.rag_service:
            self.rag_service.cleanup()


def create_ghostwriter_agent(
    agent_model: Agent,
    db_session: AsyncSession,
    google_client: genai.Client,
    api_key: str | None = None,
) -> GhostwriterAgent:
    """
    Create a Ghostwriter agent from a database model.

    Args:
        agent_model: Database agent model
        db_session: Database session
        google_client: Google GenAI client
        api_key: Optional API key override

    Returns:
        Configured Ghostwriter agent
    """
    # Create agent config from model
    config = AgentConfig(
        name=agent_model.name,
        description=agent_model.description or "Ghostwriter agent",
        system_prompt=agent_model.system_prompt
        or "You are a professional ghostwriter who can emulate different writing styles. "
        "Your goal is to create content that matches the voice and style of specific individuals.",
    )

    # Create Ghostwriter agent
    agent = GhostwriterAgent(
        config=config,
        agent_model=agent_model,
        db_session=db_session,
        google_client=google_client,
    )

    # Initialize client
    if api_key:
        agent.initialize_client(api_key)

    return agent
