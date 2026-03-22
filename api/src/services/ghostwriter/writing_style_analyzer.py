"""
Writing Style Analyzer Service.

Analyzes communication samples to extract writing style characteristics
for use in the Ghostwriter Agent.
"""

import logging
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.knowledge_base import KnowledgeBase
from src.models.writing_style_profile import WritingStyleProfile

logger = logging.getLogger(__name__)


class WritingStyleAnalyzer:
    """
    Analyzes writing samples to extract style characteristics.

    This service processes communication samples (emails, messages, documents)
    to identify patterns in tone, vocabulary, sentence structure, and
    communication style.
    """

    def __init__(self, db: AsyncSession, rag_service=None):
        """
        Initialize the analyzer.

        Args:
            db: Database session
            rag_service: Optional RAG service for vector storage
        """
        self.db = db
        self.rag_service = rag_service

    async def analyze_samples(
        self,
        tenant_id: UUID,
        person_identifier: str,
        samples: list[str],
        knowledge_base: KnowledgeBase,
        person_name: str | None = None,
        person_role: str | None = None,
    ) -> WritingStyleProfile:
        """
        Analyze writing samples and create/update a style profile.

        Args:
            tenant_id: Tenant ID
            person_identifier: Email or user ID of the person
            samples: List of text samples to analyze
            person_name: Optional person name
            person_role: Optional person role

        Returns:
            WritingStyleProfile with analyzed characteristics
        """
        if not samples:
            raise ValueError("At least one sample is required for analysis")

        logger.info(f"Analyzing {len(samples)} samples for person: {person_identifier}")

        # Check if profile exists
        stmt = select(WritingStyleProfile).where(
            WritingStyleProfile.tenant_id == tenant_id,
            WritingStyleProfile.person_identifier == person_identifier,
        )
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile:
            logger.info(f"Updating existing profile: {profile.id}")
        else:
            logger.info("Creating new profile")
            profile = WritingStyleProfile(
                tenant_id=tenant_id,
                person_identifier=person_identifier,
                person_name=person_name,
                person_role=person_role,
            )
            self.db.add(profile)

        # Analyze characteristics
        tone_chars = self._analyze_tone(samples)
        vocab_patterns = self._analyze_vocabulary(samples)
        sentence_metrics = self._analyze_sentence_structure(samples)
        comm_patterns = self._analyze_communication_patterns(samples)

        # Update profile
        profile.tone_characteristics = tone_chars
        profile.vocabulary_patterns = vocab_patterns
        profile.sentence_metrics = sentence_metrics
        profile.communication_patterns = comm_patterns
        profile.sample_count = len(samples)
        profile.confidence_score = self._calculate_confidence(len(samples))
        profile.last_analyzed_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(profile)

        if self.rag_service and knowledge_base:
            profile_text = self._create_profile_text(tone_chars, vocab_patterns, sentence_metrics, comm_patterns)

            try:
                await self.rag_service.add_documents_to_knowledge_base(
                    knowledge_base=knowledge_base,
                    documents=[
                        {
                            "id": str(profile.id),
                            "text": profile_text,
                            "metadata": {
                                "profile_id": str(profile.id),
                                "person_identifier": person_identifier,
                                "person_name": person_name or "",
                                "person_role": person_role or "",
                                "sample_count": len(samples),
                                "confidence_score": profile.confidence_score,
                                "source": f"writing_style_profile_{profile.id}",
                            },
                        }
                    ],
                )
                logger.info(f"Stored profile {profile.id} in knowledge base {knowledge_base.id}")
            except Exception as e:
                logger.warning(f"Failed to store profile in knowledge base: {e}")

        logger.info(f"Profile analysis complete. Confidence: {profile.confidence_score:.2f}")
        return profile

    def _analyze_tone(self, samples: list[str]) -> dict[str, Any]:
        """
        Analyze tone characteristics.

        Args:
            samples: Text samples

        Returns:
            Dictionary with tone metrics
        """
        # Formal indicators
        formal_words = {
            "regarding",
            "furthermore",
            "therefore",
            "consequently",
            "nevertheless",
            "accordingly",
            "hereby",
            "pursuant",
        }

        # Casual indicators
        casual_words = {
            "hey",
            "yeah",
            "yep",
            "nope",
            "gonna",
            "wanna",
            "kinda",
            "sorta",
            "btw",
            "fyi",
        }

        # Enthusiasm indicators
        enthusiasm_indicators = ["!", "!!", "!!!", "awesome", "great", "excellent"]

        formal_count = 0
        casual_count = 0
        enthusiasm_count = 0
        total_words = 0

        for sample in samples:
            words = sample.lower().split()
            total_words += len(words)

            formal_count += sum(1 for word in words if word in formal_words)
            casual_count += sum(1 for word in words if word in casual_words)

            for indicator in enthusiasm_indicators:
                enthusiasm_count += sample.count(indicator)

        # Calculate scores (0-1 scale)
        formal_score = min(formal_count / max(total_words / 100, 1), 1.0)
        casual_score = min(casual_count / max(total_words / 100, 1), 1.0)
        enthusiasm_level = min(enthusiasm_count / len(samples), 1.0)

        # Professional score (inverse of casual)
        professional_score = max(0.5, 1.0 - casual_score)

        # Friendly score (balance of casual and enthusiasm)
        friendly_score = (casual_score + enthusiasm_level) / 2

        return {
            "formal_score": round(formal_score, 3),
            "professional_score": round(professional_score, 3),
            "friendly_score": round(friendly_score, 3),
            "enthusiasm_level": round(enthusiasm_level, 3),
        }

    def _analyze_vocabulary(self, samples: list[str]) -> dict[str, Any]:
        """
        Analyze vocabulary patterns.

        Args:
            samples: Text samples

        Returns:
            Dictionary with vocabulary patterns
        """
        all_text = " ".join(samples).lower()
        words = re.findall(r"\b\w+\b", all_text)

        # Common phrases (2-3 word sequences)
        bigrams = [f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1) if len(words) > 1]
        trigrams = [f"{words[i]} {words[i + 1]} {words[i + 2]}" for i in range(len(words) - 2) if len(words) > 2]

        # Get most common phrases
        bigram_counter = Counter(bigrams)
        trigram_counter = Counter(trigrams)

        common_phrases = [phrase for phrase, count in bigram_counter.most_common(10) if count > 1] + [
            phrase for phrase, count in trigram_counter.most_common(5) if count > 1
        ]

        # Technical terms (words with specific patterns)
        technical_terms = list({word for word in words if len(word) > 8 or (word.isupper() and len(word) > 2)})[:20]

        # Greeting patterns
        greeting_patterns = []
        for sample in samples:
            first_line = sample.split("\n")[0].lower()
            if any(greeting in first_line for greeting in ["hi", "hello", "hey", "dear", "greetings"]):
                greeting_patterns.append(first_line[:50])

        # Closing patterns
        closing_patterns = []
        for sample in samples:
            lines = sample.split("\n")
            if len(lines) > 1:
                last_lines = " ".join(lines[-2:]).lower()
                if any(
                    closing in last_lines
                    for closing in [
                        "thanks",
                        "regards",
                        "best",
                        "sincerely",
                        "cheers",
                    ]
                ):
                    closing_patterns.append(last_lines[:50])

        return {
            "common_phrases": common_phrases[:15],
            "technical_terms": technical_terms[:15],
            "jargon": [],  # Could be enhanced with domain-specific detection
            "greeting_patterns": list(set(greeting_patterns))[:5],
            "closing_patterns": list(set(closing_patterns))[:5],
        }

    def _analyze_sentence_structure(self, samples: list[str]) -> dict[str, Any]:
        """
        Analyze sentence structure metrics.

        Args:
            samples: Text samples

        Returns:
            Dictionary with sentence metrics
        """
        all_sentences = []
        for sample in samples:
            # Split by sentence endings
            sentences = re.split(r"[.!?]+", sample)
            all_sentences.extend([s.strip() for s in sentences if s.strip()])

        if not all_sentences:
            return {
                "avg_sentence_length": 0,
                "complexity_score": 0.5,
                "paragraph_style": "unknown",
                "bullet_point_usage": 0.0,
                "question_frequency": 0.0,
            }

        # Average sentence length (in words)
        sentence_lengths = [len(s.split()) for s in all_sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths)

        # Complexity score (based on avg length and punctuation)
        complexity_score = min(avg_length / 20, 1.0)  # Normalize to 0-1

        # Paragraph style
        total_chars = sum(len(sample) for sample in samples)
        newline_count = sum(sample.count("\n") for sample in samples)
        avg_paragraph_length = total_chars / max(newline_count, 1) if newline_count > 0 else total_chars

        if avg_paragraph_length < 200:
            paragraph_style = "short"
        elif avg_paragraph_length < 500:
            paragraph_style = "medium"
        else:
            paragraph_style = "long"

        # Bullet point usage
        bullet_indicators = ["-", "*", "•", "1.", "2.", "3."]
        bullet_count = sum(sum(sample.count(indicator) for indicator in bullet_indicators) for sample in samples)
        bullet_usage = min(bullet_count / len(samples), 1.0)

        # Question frequency
        question_count = sum(sample.count("?") for sample in samples)
        question_freq = question_count / len(all_sentences)

        return {
            "avg_sentence_length": round(avg_length, 1),
            "complexity_score": round(complexity_score, 3),
            "paragraph_style": paragraph_style,
            "bullet_point_usage": round(bullet_usage, 3),
            "question_frequency": round(question_freq, 3),
        }

    def _analyze_communication_patterns(self, samples: list[str]) -> dict[str, Any]:
        """
        Analyze communication patterns.

        Args:
            samples: Text samples

        Returns:
            Dictionary with communication patterns
        """
        # Email subject style (if samples contain subject lines)
        subject_style = "direct"  # Could be enhanced with actual subject line analysis

        # Opening style
        opening_styles = []
        for sample in samples:
            first_sentence = sample.split(".")[0].lower()
            if "hope" in first_sentence:
                opening_styles.append("hopeful")
            elif any(word in first_sentence for word in ["hi", "hello", "hey"]):
                opening_styles.append("greeting")
            elif "wanted to" in first_sentence or "writing to" in first_sentence:
                opening_styles.append("purpose-driven")
            else:
                opening_styles.append("direct")

        opening_style = Counter(opening_styles).most_common(1)[0][0] if opening_styles else "direct"

        # Closing style
        closing_styles = []
        for sample in samples:
            last_lines = " ".join(sample.split("\n")[-2:]).lower()
            if "thanks" in last_lines or "thank you" in last_lines:
                closing_styles.append("grateful")
            elif "regards" in last_lines or "best" in last_lines:
                closing_styles.append("formal")
            elif "cheers" in last_lines:
                closing_styles.append("casual")
            else:
                closing_styles.append("simple")

        closing_style = Counter(closing_styles).most_common(1)[0][0] if closing_styles else "simple"

        # Emoji usage
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags
            "]+",
            flags=re.UNICODE,
        )

        emoji_count = sum(len(emoji_pattern.findall(sample)) for sample in samples)
        emoji_usage = min(emoji_count / len(samples), 1.0)

        # Signature style (last 2 lines)
        signatures = []
        for sample in samples:
            lines = sample.split("\n")
            if len(lines) >= 2:
                signature = "\n".join(lines[-2:])
                if len(signature) < 100:  # Reasonable signature length
                    signatures.append(signature)

        signature_style = signatures[0] if signatures else ""  # Use first as representative

        return {
            "email_subject_style": subject_style,
            "opening_style": opening_style,
            "closing_style": closing_style,
            "emoji_usage": round(emoji_usage, 3),
            "signature_style": signature_style[:100],  # Truncate if too long
        }

    def _calculate_confidence(self, sample_count: int) -> float:
        """
        Calculate confidence score based on sample count.

        Args:
            sample_count: Number of samples analyzed

        Returns:
            Confidence score (0-1)
        """
        # Confidence increases with more samples, plateaus at 50 samples
        if sample_count < 5:
            return 0.3
        elif sample_count < 10:
            return 0.5
        elif sample_count < 20:
            return 0.7
        elif sample_count < 50:
            return 0.85
        else:
            return 0.95

    def _create_profile_text(
        self,
        tone_chars: dict[str, Any],
        vocab_patterns: dict[str, Any],
        sentence_metrics: dict[str, Any],
        comm_patterns: dict[str, Any],
    ) -> str:
        """
        Create a text representation of the profile for embedding.

        Args:
            tone_chars: Tone characteristics
            vocab_patterns: Vocabulary patterns
            sentence_metrics: Sentence metrics
            comm_patterns: Communication patterns

        Returns:
            Text representation of the profile
        """
        parts = [
            f"Tone: formal={tone_chars['formal_score']}, professional={tone_chars['professional_score']}, "
            f"friendly={tone_chars['friendly_score']}, enthusiasm={tone_chars['enthusiasm_level']}",
            f"Common phrases: {', '.join(vocab_patterns['common_phrases'][:5])}",
            f"Sentence length: {sentence_metrics['avg_sentence_length']} words, "
            f"style: {sentence_metrics['paragraph_style']}",
            f"Communication: opening={comm_patterns['opening_style']}, closing={comm_patterns['closing_style']}",
        ]

        return " | ".join(parts)
