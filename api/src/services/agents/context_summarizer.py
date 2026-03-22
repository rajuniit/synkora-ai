"""
Context Summarization Service.

Provides LLM-based summarization of conversation history to compress old context.
Designed to preserve key information while reducing token count.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


# Optimized prompts for different summarization scenarios
SUMMARIZATION_PROMPTS = {
    "conversation": """You are a conversation summarizer. Create a concise summary that captures:

1. **PENDING USER REQUESTS** (MOST IMPORTANT): Any tasks/requests the user asked for that have NOT been completed yet. Include exact details (times, names, durations, etc.)
2. KEY DECISIONS: Any decisions made or agreed upon
3. IMPORTANT FACTS: Specific data, numbers, names, or configurations mentioned
4. USER PREFERENCES: Any preferences or requirements stated by the user
5. COMPLETED ACTIONS: What has actually been accomplished (not just discussed)
6. CONTEXT NEEDED: Information essential for continuing the conversation

Rules:
- ALWAYS start with pending/unfulfilled user requests - these are critical for continuity
- Be concise but preserve critical details
- Use bullet points for clarity
- Include specific values (numbers, names, settings, @mentions) exactly as mentioned
- If user asked for something and it wasn't done, mark it as "PENDING: ..."
- If the assistant encountered errors, note what task failed
- Maximum {max_length} words

Conversation to summarize:
{messages}

Summary:""",
    "technical": """Summarize this technical conversation, preserving:

1. PROBLEM DESCRIPTION: The issue or task being addressed
2. SOLUTION APPROACH: How the problem is being solved
3. CODE/CONFIG CHANGES: Specific changes made or planned
4. BLOCKERS: Any issues encountered and their resolutions
5. NEXT STEPS: What needs to be done next

Keep technical details (file names, function names, error messages) intact.
Maximum {max_length} words.

Conversation:
{messages}

Technical Summary:""",
    "incremental": """Update the existing summary with new information.

Previous Summary:
{existing_summary}

New Messages to Incorporate:
{messages}

Create an updated summary that:
1. **PRESERVE ALL PENDING REQUESTS** - Keep any unfulfilled user requests from the previous summary unless they were completed in new messages
2. Mark completed tasks as DONE and move them from pending
3. Add new requests, decisions, facts, or state changes
4. Remove only information that is truly outdated or superseded
5. Stays within {max_length} words

CRITICAL: If a user request was pending and still not completed, it MUST remain in the summary.

Updated Summary:""",
    "simple": """Summarize this conversation in {max_length} words or less:

{messages}

Focus on: decisions made, key facts, and current status.

Summary:""",
}


class ContextSummarizer:
    """Summarizes conversation context using LLM."""

    def __init__(self, llm_client: Any | None = None):
        """
        Initialize context summarizer.

        Args:
            llm_client: LLM client for generating summaries
        """
        self.llm_client = llm_client
        logger.info("ContextSummarizer initialized")

    async def summarize_messages(
        self,
        messages: list[dict[str, str]],
        max_summary_length: int = 500,
        context_prefix: str = "",
        prompt_type: str = "conversation",
    ) -> str:
        """
        Summarize a list of messages.

        Args:
            messages: Messages to summarize
            max_summary_length: Maximum length of summary in tokens
            context_prefix: Optional prefix to add context
            prompt_type: Type of summarization prompt to use

        Returns:
            Summary text
        """
        if not messages:
            return ""

        if not self.llm_client:
            return self._simple_summarize(messages, max_summary_length)

        # Format messages for prompt
        messages_text = self._format_messages(messages)

        # Select appropriate prompt
        if context_prefix and "Previous summary" in context_prefix:
            prompt_template = SUMMARIZATION_PROMPTS["incremental"]
            prompt = prompt_template.format(
                existing_summary=context_prefix.replace("Previous summary:\n", "").split("\n\nNew messages")[0],
                messages=messages_text,
                max_length=max_summary_length,
            )
        else:
            prompt_template = SUMMARIZATION_PROMPTS.get(prompt_type, SUMMARIZATION_PROMPTS["conversation"])
            prompt = prompt_template.format(messages=messages_text, max_length=max_summary_length)

        if context_prefix and "Previous summary" not in context_prefix:
            prompt = context_prefix + prompt

        try:
            # Generate summary using LLM
            summary = await self.llm_client.generate_content(
                prompt,
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=max_summary_length * 2,  # Allow some buffer
            )

            summary = summary.strip()
            logger.info(f"Generated summary for {len(messages)} messages ({len(summary)} chars)")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return self._simple_summarize(messages, max_summary_length)

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        """
        Format messages into a readable string.

        Args:
            messages: Messages to format

        Returns:
            Formatted string
        """
        formatted = []
        for _i, msg in enumerate(messages):
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")

            # Truncate very long messages
            if len(content) > 1000:
                content = content[:1000] + "..."

            formatted.append(f"[{role}]: {content}")

        return "\n\n".join(formatted)

    def _simple_summarize(self, messages: list[dict[str, str]], max_length: int) -> str:
        """
        Simple summarization by extracting key information.

        Used as fallback when LLM is not available.

        Args:
            messages: Messages to summarize
            max_length: Maximum length in tokens (approx words)

        Returns:
            Simple summary
        """
        # Extract key information
        user_messages = [msg.get("content", "") for msg in messages if msg.get("role") == "user"]

        assistant_messages = [msg.get("content", "") for msg in messages if msg.get("role") == "assistant"]

        summary_parts = []
        summary_parts.append(f"Conversation with {len(messages)} messages.")

        # Extract first request
        if user_messages:
            first_request = user_messages[0][:200]
            summary_parts.append(f"Initial request: {first_request}...")

        # Extract last exchange
        if len(user_messages) > 1:
            last_request = user_messages[-1][:150]
            summary_parts.append(f"Latest topic: {last_request}...")

        # Extract key decisions/actions from assistant
        if assistant_messages:
            # Look for action-related keywords
            action_keywords = ["I'll", "I will", "done", "completed", "created", "updated", "fixed"]
            actions = []

            for msg in assistant_messages:
                for keyword in action_keywords:
                    if keyword.lower() in msg.lower():
                        # Extract sentence containing keyword
                        sentences = msg.split(".")
                        for sentence in sentences:
                            if keyword.lower() in sentence.lower():
                                actions.append(sentence.strip()[:100])
                                break
                        break

            if actions:
                summary_parts.append(f"Actions taken: {'; '.join(actions[:3])}")

        summary = " ".join(summary_parts)

        # Truncate to max length
        max_chars = max_length * 4
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        return summary

    async def summarize_with_context(
        self,
        messages: list[dict[str, str]],
        context_type: str = "conversation",
        important_points: list[str] | None = None,
        existing_summary: str | None = None,
    ) -> dict[str, Any]:
        """
        Summarize with additional context and metadata.

        Args:
            messages: Messages to summarize
            context_type: Type of context being summarized
            important_points: Important points to highlight in summary
            existing_summary: Existing summary to update

        Returns:
            Dict with summary and metadata
        """
        # Determine prompt type based on context
        if context_type == "technical":
            prompt_type = "technical"
        elif existing_summary:
            prompt_type = "incremental"
        else:
            prompt_type = "conversation"

        context_prefix = ""
        if existing_summary:
            context_prefix = f"Previous summary:\n{existing_summary}\n\nNew messages to incorporate:\n"

        summary = await self.summarize_messages(messages, context_prefix=context_prefix, prompt_type=prompt_type)

        # Calculate compression ratio
        original_length = sum(len(msg.get("content", "")) for msg in messages)
        compression_ratio = len(summary) / original_length if original_length > 0 else 0

        return {
            "summary": summary,
            "context_type": context_type,
            "original_message_count": len(messages),
            "compression_ratio": round(compression_ratio, 3),
            "important_points": important_points or [],
            "timestamp": time.time(),
            "had_existing_summary": existing_summary is not None,
        }

    def should_summarize(
        self, messages: list[dict[str, str]], threshold_messages: int = 30, threshold_tokens: int = 50000
    ) -> bool:
        """
        Determine if messages should be summarized.

        Args:
            messages: Messages to check
            threshold_messages: Threshold for number of messages
            threshold_tokens: Threshold for total tokens

        Returns:
            True if summarization is recommended
        """
        if len(messages) >= threshold_messages:
            return True

        # Calculate total tokens (estimate)
        try:
            from src.services.agents.token_counter import TokenCounter

            total_tokens = TokenCounter.count_messages_tokens(messages)
        except ImportError:
            total_tokens = sum(len(msg.get("content", "")) // 4 for msg in messages)

        return total_tokens >= threshold_tokens

    def estimate_summary_tokens(self, messages: list[dict[str, str]], compression_ratio: float = 0.1) -> int:
        """
        Estimate tokens needed for summary.

        Args:
            messages: Messages that would be summarized
            compression_ratio: Expected compression ratio (default 10%)

        Returns:
            Estimated summary token count
        """
        try:
            from src.services.agents.token_counter import TokenCounter

            original_tokens = TokenCounter.count_messages_tokens(messages)
        except ImportError:
            original_tokens = sum(len(msg.get("content", "")) // 4 for msg in messages)

        return int(original_tokens * compression_ratio)
