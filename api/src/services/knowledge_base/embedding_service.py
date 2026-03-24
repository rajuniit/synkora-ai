"""Embedding service — delegates sentence_transformers to the ML microservice."""

import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using multiple providers.

    The ``sentence_transformers`` and ``huggingface`` providers are served by the
    ML microservice (``synkora-ml``) so that the API image does not need to bundle
    those heavy packages.  All other providers (OPENAI, cohere, LITELLM) are still
    executed in-process.
    """

    def __init__(
        self, provider: str = "sentence_transformers", model_name: str = "all-MiniLM-L6-v2", config: dict | None = None
    ):
        self.provider = provider
        self.model_name = model_name
        self.config = config or {}
        self.model = None
        self.client = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the embedding model based on provider."""
        try:
            logger.info(f"Loading embedding model: {self.provider}/{self.model_name}")

            if self.provider in ("sentence_transformers", "huggingface"):
                # Handled by ML microservice — no local model to load
                logger.info(f"Using ML microservice for provider={self.provider}")

            elif self.provider == "OPENAI":
                import openai

                api_key = self.config.get("api_key")
                if not api_key:
                    raise ValueError("OpenAI API key not provided in embedding_config")
                self.client = openai.OpenAI(api_key=api_key)

            elif self.provider == "cohere":
                import cohere

                api_key = self.config.get("api_key")
                if not api_key:
                    raise ValueError("Cohere API key not provided in embedding_config")
                self.client = cohere.Client(api_key)

            elif self.provider == "LITELLM":
                import litellm

                self.client = litellm
                if self.config.get("api_base"):
                    litellm.api_base = self.config["api_base"]
                logger.info(f"Initialized LiteLLM for embeddings with model: {self.model_name}")

            else:
                raise ValueError(f"Unsupported embedding provider: {self.provider}")

            logger.info(f"Successfully loaded model: {self.provider}/{self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        try:
            if self.provider in ("sentence_transformers", "huggingface"):
                import asyncio

                from src.core.ml_client import get_ml_client

                client = get_ml_client()
                return asyncio.run(client.embed_text(text, model=self.model_name))

            elif self.provider == "OPENAI":
                response = self.client.embeddings.create(model=self.model_name, input=text)
                return response.data[0].embedding

            elif self.provider == "cohere":
                response = self.client.embed(texts=[text], model=self.model_name)
                return response.embeddings[0]

            elif self.provider == "LITELLM":
                import litellm

                response = litellm.embedding(
                    model=self.model_name,
                    input=[text],
                    api_key=self.config.get("api_key"),
                    api_base=self.config.get("api_base"),
                )
                return response.data[0]["embedding"]

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches."""
        try:
            if self.provider in ("sentence_transformers", "huggingface"):
                import asyncio

                from src.core.ml_client import get_ml_client

                client = get_ml_client()
                # ML service handles batching internally
                return asyncio.run(client.embed(texts, model=self.model_name))

            elif self.provider == "OPENAI":
                response = self.client.embeddings.create(model=self.model_name, input=texts)
                return [item.embedding for item in response.data]

            elif self.provider == "cohere":
                response = self.client.embed(texts=texts, model=self.model_name)
                return response.embeddings

            elif self.provider == "LITELLM":
                import litellm

                response = litellm.embedding(
                    model=self.model_name,
                    input=texts,
                    api_key=self.config.get("api_key"),
                    api_base=self.config.get("api_base"),
                )
                return [item["embedding"] for item in response.data]

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        if "dimension" in self.config:
            return self.config["dimension"]

        if self.provider in ("sentence_transformers", "huggingface"):
            import asyncio

            from src.core.ml_client import get_ml_client

            client = get_ml_client()
            return asyncio.run(client.get_embedding_dimension(model=self.model_name))

        raise ValueError(
            f"Embedding dimension not configured for provider '{self.provider}'. "
            "Please specify 'dimension' in embedding_config."
        )
