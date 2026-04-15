"""
Diagram generation service.

Provides a deterministic SVG rendering engine for technical diagrams.
The LLM generates a structured JSON spec; this engine renders pixel-perfect SVG.
"""

from src.services.diagrams.svg_renderer import DiagramRenderer

__all__ = ["DiagramRenderer"]
