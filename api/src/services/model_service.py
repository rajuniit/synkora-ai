"""
Model service for managing LLM interactions.

This service integrates model providers with the conversation system.
"""

from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError, ValidationError
from src.core.model_providers import (
    BaseModelProvider,
    ModelConfig,
    ModelProviderFactory,
    ModelResponse,
)
from src.models import App, MessageRole, MessageStatus

from .conversation_service import ConversationService


class ModelService:
    """Service for managing model interactions."""

    def __init__(self, db: AsyncSession):
        """
        Initialize model service.

        Args:
            db: Database session
        """
        self.db = db
        self.conversation_service = ConversationService(db)

    def _get_provider_from_app(self, app: App) -> BaseModelProvider:
        """
        Get model provider from app configuration.

        Args:
            app: App instance

        Returns:
            Model provider instance

        Raises:
            ValidationError: If provider configuration is invalid
        """
        model_config = app.model_config or {}

        if "provider" not in model_config:
            raise ValidationError("Model provider not configured for app")

        if "api_key" not in model_config:
            raise ValidationError("API key not configured for app")

        return ModelProviderFactory.create_from_config(model_config)

    def _get_model_config_from_app(self, app: App) -> ModelConfig:
        """
        Get model configuration from app.

        Args:
            app: App instance

        Returns:
            Model configuration

        Raises:
            ValidationError: If configuration is invalid
        """
        config = app.model_config or {}

        if "model" not in config:
            raise ValidationError("Model not specified in app configuration")

        return ModelConfig(
            model=config["model"],
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 1000),
            top_p=config.get("top_p", 1.0),
            frequency_penalty=config.get("frequency_penalty", 0.0),
            presence_penalty=config.get("presence_penalty", 0.0),
            stop=config.get("stop"),
            stream=config.get("stream", False),
        )

    async def generate_response(
        self,
        conversation_id: UUID,
        user_message: str,
        stream: bool = False,
    ) -> ModelResponse | AsyncIterator[str]:
        """
        Generate a response for a conversation.

        Args:
            conversation_id: Conversation ID
            user_message: User's message
            stream: Whether to stream the response

        Returns:
            Model response or async iterator of chunks

        Raises:
            NotFoundError: If conversation not found
            ValidationError: If configuration is invalid
        """
        # Get conversation with app
        conversation = await self.conversation_service.get_conversation(conversation_id, include_messages=True)

        # Get app
        app = await self.db.get(App, conversation.app_id)
        if not app:
            raise NotFoundError("App not found")

        # Add user message
        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=user_message,
        )

        # Get provider and config
        provider = self._get_provider_from_app(app)
        config = self._get_model_config_from_app(app)
        config.stream = stream

        # Build message history
        messages = []
        for msg in conversation.messages:
            if msg.is_completed():
                messages.append(
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                    }
                )

        # Generate response
        if stream:
            return self._generate_stream(
                provider=provider,
                config=config,
                messages=messages,
                conversation_id=conversation_id,
            )
        else:
            return await self._generate_complete(
                provider=provider,
                config=config,
                messages=messages,
                conversation_id=conversation_id,
            )

    async def _generate_complete(
        self,
        provider: BaseModelProvider,
        config: ModelConfig,
        messages: list[dict[str, str]],
        conversation_id: UUID,
    ) -> ModelResponse:
        """
        Generate a complete response.

        Args:
            provider: Model provider
            config: Model configuration
            messages: Message history
            conversation_id: Conversation ID

        Returns:
            Model response
        """
        # Create assistant message in pending state
        assistant_msg = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="",
            metadata={"status": "pending"},
        )

        try:
            # Update to processing
            await self.conversation_service.update_message_status(assistant_msg.id, MessageStatus.PROCESSING)

            # Generate response
            response = await provider.generate(messages, config)

            # Update message with response
            assistant_msg.content = response.content
            assistant_msg.message_metadata = {
                "model": response.model,
                "usage": response.usage,
                "finish_reason": response.finish_reason,
            }
            assistant_msg.token_count = response.usage.get("total_tokens", 0)

            await self.conversation_service.update_message_status(assistant_msg.id, MessageStatus.COMPLETED)

            return response

        except Exception as e:
            # Update message with error
            await self.conversation_service.update_message_status(assistant_msg.id, MessageStatus.FAILED, error=str(e))
            raise

    async def _generate_stream(
        self,
        provider: BaseModelProvider,
        config: ModelConfig,
        messages: list[dict[str, str]],
        conversation_id: UUID,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response.

        Args:
            provider: Model provider
            config: Model configuration
            messages: Message history
            conversation_id: Conversation ID

        Yields:
            Content chunks
        """
        # Create assistant message in pending state
        assistant_msg = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="",
            metadata={"status": "pending"},
        )

        try:
            # Update to processing
            await self.conversation_service.update_message_status(assistant_msg.id, MessageStatus.PROCESSING)

            # Stream response
            full_content = ""
            stream_gen = provider.generate_stream(messages, config)
            async for chunk in stream_gen:
                full_content += chunk
                yield chunk

            # Update message with full content
            assistant_msg.content = full_content
            await self.conversation_service.update_message_status(assistant_msg.id, MessageStatus.COMPLETED)

        except Exception as e:
            # Update message with error
            await self.conversation_service.update_message_status(assistant_msg.id, MessageStatus.FAILED, error=str(e))
            raise

    async def validate_app_model_config(self, app: App) -> bool:
        """
        Validate app's model configuration.

        Args:
            app: App instance

        Returns:
            True if configuration is valid

        Raises:
            ValidationError: If configuration is invalid
        """
        provider = self._get_provider_from_app(app)
        return await provider.validate_credentials()
