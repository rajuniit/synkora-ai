"""Embedding service for generating vector embeddings."""

import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using multiple providers."""

    def __init__(
        self, provider: str = "sentence_transformers", model_name: str = "all-MiniLM-L6-v2", config: dict | None = None
    ):
        """
        Initialize the embedding service.

        Args:
            provider: Embedding provider ('sentence_transformers', 'OPENAI', 'cohere', 'huggingface', 'LITELLM')
            model_name: Name of the model to use
            config: Provider-specific configuration (API keys, api_base, etc.)
        """
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

            if self.provider == "sentence_transformers":
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(self.model_name)

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

            elif self.provider == "huggingface":
                from sentence_transformers import SentenceTransformer

                # HuggingFace models can be loaded via sentence-transformers
                self.model = SentenceTransformer(self.model_name)

            elif self.provider == "LITELLM":
                import litellm

                # LiteLLM doesn't need a client object, it's a function-based API
                # It routes to the appropriate provider based on model name prefix
                # e.g., "openai/text-embedding-ada-002", "cohere/embed-english-v3.0"
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
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            if self.provider in ["sentence_transformers", "huggingface"]:
                if not self.model:
                    raise RuntimeError("Embedding model not loaded")
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding.tolist()

            elif self.provider == "OPENAI":
                response = self.client.embeddings.create(model=self.model_name, input=text)
                return response.data[0].embedding

            elif self.provider == "cohere":
                response = self.client.embed(texts=[text], model=self.model_name)
                return response.embeddings[0]

            elif self.provider == "LITELLM":
                import litellm

                # LiteLLM embedding API
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
        """
        Generate embeddings for multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch

        Returns:
            List of embedding vectors
        """
        try:
            if self.provider in ["sentence_transformers", "huggingface"]:
                if not self.model:
                    raise RuntimeError("Embedding model not loaded")
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=len(texts) > 100,
                    convert_to_numpy=True,
                )
                return [emb.tolist() for emb in embeddings]

            elif self.provider == "OPENAI":
                # OpenAI supports batch embedding
                response = self.client.embeddings.create(model=self.model_name, input=texts)
                return [item.embedding for item in response.data]

            elif self.provider == "cohere":
                # Cohere supports batch embedding
                response = self.client.embed(texts=texts, model=self.model_name)
                return response.embeddings

            elif self.provider == "LITELLM":
                import litellm

                # LiteLLM supports batch embedding
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
        """
        Get the dimension of the embedding vectors.

        Returns:
            Dimension of the embedding vectors
        """
        # Always use dimension from config if provided
        if "dimension" in self.config:
            return self.config["dimension"]

        # For sentence transformers, we can get it from the model
        if self.provider in ["sentence_transformers", "huggingface"]:
            if not self.model:
                raise RuntimeError("Embedding model not loaded")
            return self.model.get_sentence_embedding_dimension()

        # For all other providers (OPENAI, cohere, LITELLM), dimension must be configured
        raise ValueError(
            f"Embedding dimension not configured for provider '{self.provider}'. "
            "Please specify 'dimension' in embedding_config."
        )
