"""
Research Agent implementation using Google Agent SDK.

Provides an agent specialized for research tasks with web search capabilities.
"""

import logging
from typing import Any

from google.genai import types

from src.services.agents.base_agent import BaseAgent
from src.services.agents.config import AgentConfig, ToolConfig

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """
    Research agent with web search and analysis capabilities.

    This agent can:
    - Search the web for information
    - Analyze and synthesize research findings
    - Generate comprehensive research reports
    - Cite sources
    """

    client: Any = None

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the research agent.

        Args:
            input_data: Dictionary containing:
                - query: Research query/question
                - depth: Research depth (quick, standard, deep)
                - max_sources: Maximum number of sources to use

        Returns:
            Dictionary containing:
                - findings: Research findings
                - sources: List of sources used
                - summary: Executive summary
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call initialize_client() first.")

        query = input_data.get("query")
        if not query:
            raise ValueError("'query' is required in input_data")

        depth = input_data.get("depth", "standard")
        max_sources = input_data.get("max_sources", 5)

        try:
            # Build research prompt
            research_prompt = f"""
You are a research assistant. Conduct thorough research on the following query:

Query: {query}

Research Depth: {depth}
Maximum Sources: {max_sources}

Please provide:
1. Key findings from your research
2. A comprehensive analysis
3. An executive summary
4. Relevant sources (if available)

Format your response as a structured research report.
"""

            # Generate research response
            response = self.client.models.generate_content(
                model=self.config.llm_config.model_name,
                contents=research_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for factual research
                    max_output_tokens=2048,
                ),
            )

            response_text = response.text if hasattr(response, "text") else str(response)

            # Parse response (simplified - in production, use structured output)
            findings = self._extract_section(response_text, "findings")
            summary = self._extract_section(response_text, "summary")

            logger.info(f"Research agent completed query: {query[:50]}...")

            return {
                "query": query,
                "findings": findings or response_text,
                "summary": summary or "Research completed successfully",
                "depth": depth,
                "model": self.config.llm_config.model_name,
            }

        except Exception as e:
            logger.error(f"Research agent execution failed: {e}", exc_info=True)
            raise

    def _extract_section(self, text: str, section: str) -> str:
        """
        Extract a section from the response text.

        Args:
            text: Full response text
            section: Section name to extract

        Returns:
            Extracted section text
        """
        # Simple extraction - in production, use more robust parsing
        lines = text.split("\n")
        section_lines = []
        in_section = False

        for line in lines:
            if not in_section and section.lower() in line.lower():
                in_section = True
                continue
            if in_section:
                if line.strip() and not line.strip().startswith("#"):
                    section_lines.append(line)
                elif len(section_lines) > 0 and line.strip().startswith("#"):
                    break

        return "\n".join(section_lines).strip()


def create_research_agent(api_key: str) -> ResearchAgent:
    """
    Create a pre-configured research agent.

    Args:
        api_key: Google API key

    Returns:
        Configured research agent
    """
    config = AgentConfig(
        name="research_agent",
        description="Research agent with web search and analysis capabilities",
        system_prompt=(
            "You are an expert research assistant. Your role is to conduct thorough research, "
            "analyze information critically, and provide well-structured, evidence-based reports. "
            "Always cite sources when possible and present information objectively."
        ),
        tools=[
            ToolConfig(
                name="web_search",
                description="Search the web for information",
                enabled=True,
            ),
        ],
    )

    agent = ResearchAgent(config)
    agent.initialize_client(api_key)

    return agent
