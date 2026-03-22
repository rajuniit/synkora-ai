"""
Code Agent implementation using Google Agent SDK.

Provides an agent specialized for code generation, analysis, and debugging.
"""

import logging
from typing import Any

from google.genai import types

from src.services.agents.base_agent import BaseAgent
from src.services.agents.config import AgentConfig, ToolConfig

logger = logging.getLogger(__name__)


class CodeAgent(BaseAgent):
    """
    Code agent specialized for software development tasks.

    This agent can:
    - Generate code in multiple languages
    - Review and analyze existing code
    - Debug and fix code issues
    - Explain code functionality
    - Suggest improvements and optimizations
    """

    client: Any = None

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the code agent.

        Args:
            input_data: Dictionary containing:
                - task: Task type (generate, review, debug, explain)
                - language: Programming language
                - code: Existing code (for review/debug/explain)
                - requirements: Requirements for code generation
                - context: Additional context

        Returns:
            Dictionary containing:
                - result: Generated/analyzed code or explanation
                - language: Programming language used
                - suggestions: Optional improvement suggestions
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call initialize_client() first.")

        task = input_data.get("task", "generate")
        language = input_data.get("language", "python")
        code = input_data.get("code", "")
        requirements = input_data.get("requirements", "")
        context = input_data.get("context", "")

        if not requirements and not code:
            raise ValueError("Either 'requirements' or 'code' must be provided")

        try:
            # Build task-specific prompt
            if task == "generate":
                prompt = self._build_generation_prompt(language, requirements, context)
            elif task == "review":
                prompt = self._build_review_prompt(language, code, context)
            elif task == "debug":
                prompt = self._build_debug_prompt(language, code, context)
            elif task == "explain":
                prompt = self._build_explain_prompt(language, code, context)
            else:
                raise ValueError(f"Unknown task type: {task}")

            # Generate response
            response = self.client.models.generate_content(
                model=self.config.llm_config.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,  # Lower temperature for code tasks
                    max_output_tokens=2048,
                ),
            )

            response_text = response.text if hasattr(response, "text") else str(response)

            logger.info(f"Code agent completed {task} task for {language}")

            return {
                "task": task,
                "language": language,
                "result": response_text,
                "model": self.config.llm_config.model_name,
            }

        except Exception as e:
            logger.error(f"Code agent execution failed: {e}", exc_info=True)
            raise

    def _build_generation_prompt(self, language: str, requirements: str, context: str) -> str:
        """Build prompt for code generation."""
        prompt = f"""
You are an expert {language} developer. Generate clean, efficient, and well-documented code.

Requirements:
{requirements}
"""
        if context:
            prompt += f"\nContext:\n{context}\n"

        prompt += f"""
Please provide:
1. Complete, working {language} code
2. Inline comments explaining key logic
3. Usage examples if applicable
4. Any important notes or considerations

Format your response with proper code blocks.
"""
        return prompt

    def _build_review_prompt(self, language: str, code: str, context: str) -> str:
        """Build prompt for code review."""
        prompt = f"""
You are an expert {language} code reviewer. Review the following code for:
- Code quality and best practices
- Potential bugs or issues
- Performance optimizations
- Security concerns
- Maintainability

Code to review:
```{language}
{code}
```
"""
        if context:
            prompt += f"\nContext:\n{context}\n"

        prompt += """
Please provide:
1. Overall assessment
2. Specific issues found (if any)
3. Suggestions for improvement
4. Positive aspects of the code
"""
        return prompt

    def _build_debug_prompt(self, language: str, code: str, context: str) -> str:
        """Build prompt for debugging."""
        prompt = f"""
You are an expert {language} debugger. Analyze the following code to identify and fix issues.

Code with issues:
```{language}
{code}
```
"""
        if context:
            prompt += f"\nError/Issue Description:\n{context}\n"

        prompt += """
Please provide:
1. Identified issues and their causes
2. Fixed code with corrections
3. Explanation of the fixes
4. Prevention tips for similar issues
"""
        return prompt

    def _build_explain_prompt(self, language: str, code: str, context: str) -> str:
        """Build prompt for code explanation."""
        prompt = f"""
You are an expert {language} developer. Explain the following code in clear, understandable terms.

Code to explain:
```{language}
{code}
```
"""
        if context:
            prompt += f"\nAdditional Context:\n{context}\n"

        prompt += """
Please provide:
1. High-level overview of what the code does
2. Step-by-step explanation of key parts
3. Explanation of any complex logic or algorithms
4. Purpose and use cases
"""
        return prompt


def create_code_agent(api_key: str, default_language: str = "python") -> CodeAgent:
    """
    Create a pre-configured code agent.

    Args:
        api_key: Google API key
        default_language: Default programming language

    Returns:
        Configured code agent
    """
    config = AgentConfig(
        name="code_agent",
        description=f"Code agent specialized for {default_language} development",
        system_prompt=(
            f"You are an expert {default_language} developer with deep knowledge of "
            "software engineering best practices, design patterns, and code quality. "
            "You write clean, efficient, well-documented code and provide insightful "
            "code reviews and debugging assistance."
        ),
        tools=[
            ToolConfig(
                name="code_execution",
                description="Execute code snippets for testing",
                enabled=False,  # Disabled by default for security
            ),
        ],
    )

    agent = CodeAgent(config)
    agent.initialize_client(api_key)

    return agent
