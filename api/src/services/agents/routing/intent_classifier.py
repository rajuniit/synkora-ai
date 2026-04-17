"""
Intent Classifier for model routing.

Pure Python — no API calls, no DB queries, no external dependencies.
Classifies user queries into intent categories and estimates complexity
so the model router can pick the cheapest model that fits the task.

Classification takes < 1ms and adds no cost.
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Intent pattern registry
# Each entry is a list of compiled regex patterns.  The intent with the
# most pattern matches wins.  Patterns are matched case-insensitively.
# ---------------------------------------------------------------------------
_RAW_PATTERNS: dict[str, list[str]] = {
    "code": [
        r"\b(write|generate|create|fix|debug|refactor|implement|optimize)\b.{0,40}\b(code|function|class|method|script|module|program|algorithm)\b",
        r"\b(function|class|method|def |async def |lambda|decorator|iterator|generator)\b",
        r"\b(python|javascript|typescript|sql|bash|shell|rust|go|java|kotlin|swift|c\+\+|c#|ruby|php|scala|dart)\b",
        r"```",
        r"\b(syntax error|runtime error|exception|stack trace|traceback|import error|type error)\b",
        r"\b(unit test|pytest|jest|mocha|test case|mock|stub|fixture)\b",
        r"\b(api endpoint|rest api|graphql|webhook|http request|fetch|axios)\b",
        r"\b(database query|sql query|orm|sqlalchemy|prisma|sequelize)\b",
        r"\b(docker|kubernetes|ci/cd|github actions|deployment|containerize)\b",
    ],
    "math": [
        r"\b(calculate|compute|solve|evaluate|simplify|differentiate|integrate|derive)\b",
        r"\b(equation|formula|theorem|proof|matrix|vector|eigenvalue|derivative|integral|limit)\b",
        r"\b(probability|statistics|regression|distribution|variance|standard deviation)\b",
        r"[=+\-*/^]{2,}",  # dense operators
        r"\b(polynomial|quadratic|linear|exponential|logarithm|trigonometry)\b",
        r"\b(\d+\s*[+\-*/^]\s*\d+|\d+\s*=\s*\d+)",  # arithmetic expressions
    ],
    "research": [
        r"\b(research|analyze|summarize|compare|contrast|evaluate|review|study|investigate)\b",
        r"\b(what is|what are|how does|why does|explain|describe|overview|introduction to)\b",
        r"\b(history|background|context|origin|evolution|development of)\b",
        r"\b(pros and cons|advantages|disadvantages|trade-offs|benefits|drawbacks)\b",
        r"\b(report|essay|article|paper|literature review|case study)\b",
        r"\b(market|industry|competitive analysis|landscape|trend)\b",
    ],
    "creative": [
        r"\b(write|compose|draft|create|generate)\b.{0,30}\b(story|poem|essay|email|blog|post|caption|tagline|slogan|copy)\b",
        r"\b(creative|imaginative|fictional|narrative|character|plot|setting)\b",
        r"\b(marketing copy|ad copy|product description|sales pitch|persuasive)\b",
        r"\b(song|lyrics|script|dialogue|speech|presentation)\b",
    ],
    "data_analysis": [
        r"\b(analyze|analyse|visualize|chart|graph|plot|dashboard|report)\b.{0,30}\b(data|dataset|csv|spreadsheet|table)\b",
        r"\b(pandas|numpy|matplotlib|seaborn|plotly|tableau|power bi)\b",
        r"\b(correlation|aggregation|pivot|group by|filter|sort|join|merge)\b",
        r"\b(insight|pattern|anomaly|outlier|trend|forecast|prediction)\b",
    ],
    "simple_qa": [
        r"^.{0,80}\?$",  # short single question
        r"^\s*(what|who|where|when|which|how|why|is|are|can|does|do|did|will|would|could|should)\b.{0,60}\?",
        r"\b(define|definition|meaning of|what does .{0,20} mean)\b",
        r"\b(list|give me|name|tell me)\b.{0,30}\b(top \d|few|some|examples?)\b",
    ],
    "reasoning": [
        r"\b(reason|infer|conclude|deduce|logic|argument|premise|hypothesis|assumption)\b",
        r"\b(multi.?step|step.by.step|chain of thought|break down|systematically)\b",
        r"\b(complex|nuanced|ambiguous|contradictory|paradox|dilemma|scenario)\b",
        r"\b(if .{0,40} then|given that|assuming that|suppose that)\b",
        r"\b(strategy|plan|roadmap|approach|framework|methodology)\b",
    ],
}

# Compile once at import time
INTENT_PATTERNS: dict[str, list[re.Pattern]] = {
    intent: [re.compile(p, re.IGNORECASE) for p in patterns] for intent, patterns in _RAW_PATTERNS.items()
}

# ---------------------------------------------------------------------------
# Complexity signals with weights (sum → 0.0–1.0)
# ---------------------------------------------------------------------------
_COMPLEXITY_SIGNALS: list[tuple[str, float, re.Pattern]] = [
    # Length-based
    ("long_query_200", 0.25, re.compile(r"(?s).{800,}")),  # > ~200 words
    ("long_query_80", 0.12, re.compile(r"(?s).{300,}")),  # > ~80 words
    # Multi-step reasoning
    (
        "multi_step",
        0.20,
        re.compile(
            r"\b(then|after that|next step|step \d|first .{0,30} then|finally|additionally|furthermore)\b",
            re.IGNORECASE,
        ),
    ),
    # Architectural / technical depth
    (
        "architecture",
        0.20,
        re.compile(
            r"\b(design|architect|trade-off|bottleneck|scalab|performance|optim|refactor|migrate|integrate)\b",
            re.IGNORECASE,
        ),
    ),
    # Code + explanation combo
    (
        "code_explain",
        0.15,
        re.compile(
            r"(explain|why|how).{0,50}(code|function|algorithm|approach)",
            re.IGNORECASE,
        ),
    ),
    # Comparative / evaluative
    (
        "comparative",
        0.10,
        re.compile(
            r"\b(compare|versus|vs\.?|difference between|which is better|pros and cons|trade.?off)\b",
            re.IGNORECASE,
        ),
    ),
    # Constraints / requirements
    (
        "constraints",
        0.10,
        re.compile(
            r"\b(must|should|require|constraint|limitation|edge case|handle|consider)\b.{0,60}\b(also|and|but|however)\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass
class ClassificationResult:
    """Result of intent + complexity classification."""

    intent: str
    """Primary task category: code | math | research | creative | data_analysis | simple_qa | reasoning | general"""

    complexity: float
    """Estimated complexity 0.0 (trivial) to 1.0 (very complex)."""

    estimated_input_tokens: int
    """Rough estimate of input tokens (query + history)."""

    intent_scores: dict[str, int]
    """Raw pattern match counts per intent (for debugging / logging)."""


class IntentClassifier:
    """
    Rule-based query intent and complexity classifier.

    Thread-safe, stateless, zero external dependencies.
    """

    def classify(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
    ) -> ClassificationResult:
        """
        Classify a user query.

        Args:
            query: The user's current message.
            conversation_history: Prior conversation turns (dicts with "role"/"content").

        Returns:
            ClassificationResult with intent, complexity, and token estimate.
        """
        intent, scores = self._detect_intent(query)
        complexity = self._estimate_complexity(query, conversation_history)
        estimated_tokens = self._estimate_tokens(query, conversation_history)

        return ClassificationResult(
            intent=intent,
            complexity=complexity,
            estimated_input_tokens=estimated_tokens,
            intent_scores=scores,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_intent(self, query: str) -> tuple[str, dict[str, int]]:
        scores: dict[str, int] = {}
        for intent, patterns in INTENT_PATTERNS.items():
            scores[intent] = sum(1 for p in patterns if p.search(query))

        best_intent = max(scores, key=lambda k: scores[k])
        if scores[best_intent] == 0:
            return "general", scores

        return best_intent, scores

    def _estimate_complexity(
        self,
        query: str,
        history: list[dict] | None,
    ) -> float:
        score = 0.0
        for _name, weight, pattern in _COMPLEXITY_SIGNALS:
            if pattern.search(query):
                score += weight

        # Deep conversation history adds complexity
        if history:
            turn_count = len(history)
            if turn_count > 20:
                score += 0.15
            elif turn_count > 10:
                score += 0.08
            elif turn_count > 5:
                score += 0.04

        return min(score, 1.0)

    @staticmethod
    def _estimate_tokens(query: str, history: list[dict] | None) -> int:
        # ~1.3 tokens per word is a reasonable approximation across models
        query_tokens = int(len(query.split()) * 1.3)
        history_tokens = 0
        if history:
            history_text = " ".join(m.get("content", "") for m in history)
            history_tokens = int(len(history_text.split()) * 1.3)
        return query_tokens + history_tokens


# Module-level singleton — cheap to create, reuse across requests
_classifier = IntentClassifier()


def classify_query(
    query: str,
    conversation_history: list[dict] | None = None,
) -> ClassificationResult:
    """Convenience function using the module-level singleton classifier."""
    return _classifier.classify(query, conversation_history)
