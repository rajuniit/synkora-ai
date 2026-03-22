"""
Test Scenario Model

Database model for storing reusable test scenarios with prompts.
"""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class TestScenario(BaseModel):
    """
    Test scenario model for reusable test configurations.

    Stores named scenarios with prompts and weights for
    distributed load testing across different use cases.

    Attributes:
        load_test_id: Parent load test
        name: Scenario name
        description: Scenario description
        weight: Distribution weight (higher = more frequent)
        prompts: List of prompt configurations
        think_time_config: Think time between requests
        variables: Variable definitions for prompt templating
    """

    __tablename__ = "test_scenarios"

    load_test_id = Column(
        UUID(as_uuid=True),
        ForeignKey("load_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent load test",
    )

    name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Scenario name",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Scenario description",
    )

    # Weight for scenario distribution (higher = more frequent)
    weight = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Distribution weight (1-100)",
    )

    # Prompt configurations
    prompts = Column(
        JSON,
        nullable=False,
        default=list,
        comment="""Array of prompt configurations:
        [
            {
                "role": "user",
                "content": "Tell me about {{topic}}",
                "is_template": true
            },
            {
                "role": "system",
                "content": "You are a helpful assistant.",
                "is_template": false
            }
        ]
        """,
    )

    # Think time configuration (ms between requests within scenario)
    think_time_config = Column(
        JSON,
        nullable=True,
        comment="""Think time configuration:
        - min_ms: Minimum think time
        - max_ms: Maximum think time
        - distribution: "uniform", "exponential", "constant"
        """,
    )

    # Variables for prompt templating
    variables = Column(
        JSON,
        nullable=True,
        comment="""Variable definitions for prompt templating:
        {
            "topic": {
                "type": "list",
                "values": ["AI", "Python", "Cloud Computing"]
            },
            "length": {
                "type": "random_int",
                "min": 100,
                "max": 500
            }
        }
        """,
    )

    # Request overrides specific to this scenario
    request_overrides = Column(
        JSON,
        nullable=True,
        comment="""Request configuration overrides:
        - model: Override model for this scenario
        - temperature: Override temperature
        - max_tokens: Override max tokens
        - stream: Override streaming setting
        """,
    )

    # Display order
    display_order = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Display order in UI",
    )

    # Relationships
    load_test = relationship("LoadTest", back_populates="scenarios", lazy="select")

    # Table indices
    __table_args__ = (Index("ix_test_scenarios_load_test_order", "load_test_id", "display_order"),)

    def __repr__(self) -> str:
        """String representation of test scenario."""
        return f"<TestScenario(id={self.id}, name='{self.name}', weight={self.weight})>"

    def render_prompt(self, prompt_index: int = 0) -> dict:
        """
        Render a prompt with variable substitution.

        Args:
            prompt_index: Index of prompt to render

        Returns:
            dict: Rendered prompt with role and content
        """
        import random
        import re

        if not self.prompts or prompt_index >= len(self.prompts):
            return {"role": "user", "content": "Hello"}

        prompt = self.prompts[prompt_index].copy()

        if not prompt.get("is_template", False):
            return prompt

        content = prompt["content"]
        variables = self.variables or {}

        # Replace template variables
        def replace_var(match):
            var_name = match.group(1)
            if var_name not in variables:
                return match.group(0)

            var_config = variables[var_name]
            var_type = var_config.get("type", "list")

            if var_type == "list":
                values = var_config.get("values", [])
                return random.choice(values) if values else ""
            elif var_type == "random_int":
                min_val = var_config.get("min", 0)
                max_val = var_config.get("max", 100)
                return str(random.randint(min_val, max_val))
            elif var_type == "random_float":
                min_val = var_config.get("min", 0.0)
                max_val = var_config.get("max", 1.0)
                return f"{random.uniform(min_val, max_val):.2f}"
            elif var_type == "uuid":
                import uuid

                return str(uuid.uuid4())
            else:
                return match.group(0)

        # Match {{variable}} patterns
        rendered_content = re.sub(r"\{\{(\w+)\}\}", replace_var, content)

        return {"role": prompt.get("role", "user"), "content": rendered_content}

    def get_think_time_ms(self) -> int:
        """
        Get think time in milliseconds based on configuration.

        Returns:
            int: Think time in milliseconds
        """
        import random

        config = self.think_time_config or {}
        min_ms = config.get("min_ms", 1000)
        max_ms = config.get("max_ms", 3000)
        distribution = config.get("distribution", "uniform")

        if distribution == "constant":
            return min_ms
        elif distribution == "exponential":
            # Exponential distribution with mean at midpoint
            mean = (min_ms + max_ms) / 2
            value = random.expovariate(1 / mean)
            return int(max(min_ms, min(max_ms, value)))
        else:  # uniform
            return random.randint(min_ms, max_ms)
