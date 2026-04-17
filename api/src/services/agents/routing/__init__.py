"""
Model routing module.

Classifies query intent and complexity, then selects the optimal
AgentLLMConfig from the agent's configured set to reduce cost while
maintaining quality.
"""

from .intent_classifier import ClassificationResult, IntentClassifier, classify_query
from .model_router import ModelRouter, RoutingDecision, get_router

__all__ = ["IntentClassifier", "ClassificationResult", "classify_query", "ModelRouter", "RoutingDecision", "get_router"]
