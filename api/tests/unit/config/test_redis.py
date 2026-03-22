"""Tests for Redis configuration."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import redis

from src.config.redis import (
    RedisConfig,
    close_redis,
    get_redis,
)


class TestRedisConfig:
    """Tests for RedisConfig class."""

    @patch.dict("os.environ", {}, clear=True)
    def test_redis_config_creation(self):
        """Test creating Redis config with URL."""
        # Clear env to test default value
        config = RedisConfig(redis_url="redis://localhost:6379/0")
        assert config.redis_url_str == "redis://localhost:6379/0"
        assert config.redis_max_connections == 50  # Default per-pod (50/pod × N pods)

    def test_redis_config_custom_max_connections(self):
        """Test custom max connections."""
        config = RedisConfig(redis_url="redis://localhost:6379/0", redis_max_connections=100)
        assert config.redis_max_connections == 100

    @patch.dict("os.environ", {"REDIS_MAX_CONNECTIONS": "50"})
    def test_redis_config_from_env(self):
        """Test Redis config reads from environment."""
        config = RedisConfig(redis_url="redis://localhost:6379/0")
        assert config.redis_max_connections == 50

    def test_redis_url_str_property(self):
        """Test redis_url_str property."""
        config = RedisConfig(redis_url="redis://localhost:6379/1")
        assert isinstance(config.redis_url_str, str)
        assert "redis://" in config.redis_url_str


class TestGetRedis:
    """Tests for get_redis function."""

    def setup_method(self):
        """Reset global redis client before each test."""
        import src.config.redis as redis_module

        redis_module._redis_client = None

    def teardown_method(self):
        """Clean up after each test."""
        import src.config.redis as redis_module

        redis_module._redis_client = None

    @patch("src.config.redis.redis.ConnectionPool.from_url")
    @patch("src.config.redis.redis.Redis")
    @patch("src.config.redis.os.getenv", return_value=None)
    def test_get_redis_creates_client(self, mock_getenv, mock_redis_class, mock_from_url):
        """Test that get_redis creates a Redis client."""
        # Setup mocks
        mock_pool = Mock()
        mock_from_url.return_value = mock_pool

        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance

        # Mock settings
        mock_settings = Mock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.redis_max_connections = 50

        with patch("src.config.settings.settings", mock_settings):
            # Call get_redis
            client = get_redis()

        # Verify
        assert client == mock_redis_instance
        mock_redis_instance.ping.assert_called_once()

    @patch("src.config.redis.redis.ConnectionPool.from_url")
    @patch("src.config.redis.redis.Redis")
    @patch("src.config.redis.os.getenv", return_value=None)
    def test_get_redis_returns_existing_client(self, mock_getenv, mock_redis_class, mock_from_url):
        """Test that get_redis returns existing client on second call."""
        # Setup mocks
        mock_pool = Mock()
        mock_from_url.return_value = mock_pool

        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance

        # Mock settings
        mock_settings = Mock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.redis_max_connections = 50

        with patch("src.config.settings.settings", mock_settings):
            # Call get_redis twice
            client1 = get_redis()
            client2 = get_redis()

        # Verify same instance returned and from_url called only once
        assert client1 == client2
        assert mock_from_url.call_count == 1

    @patch("src.config.redis.redis.ConnectionPool.from_url")
    @patch("src.config.redis.os.getenv", return_value=None)
    def test_get_redis_connection_failure(self, mock_getenv, mock_from_url):
        """Test get_redis handles connection failures."""
        # Setup mocks
        mock_from_url.side_effect = redis.ConnectionError("Connection refused")

        # Mock settings
        mock_settings = Mock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.redis_max_connections = 50

        with patch("src.config.settings.settings", mock_settings):
            # Verify exception is raised
            with pytest.raises(redis.ConnectionError):
                get_redis()

    @patch("src.config.redis.redis.ConnectionPool.from_url")
    @patch("src.config.redis.redis.Redis")
    @patch("src.config.redis.os.getenv", return_value=None)
    def test_get_redis_ping_failure(self, mock_getenv, mock_redis_class, mock_from_url):
        """Test get_redis handles ping failures."""
        # Setup mocks
        mock_pool = Mock()
        mock_from_url.return_value = mock_pool

        mock_redis_instance = Mock()
        mock_redis_instance.ping.side_effect = redis.ConnectionError("Ping failed")
        mock_redis_class.return_value = mock_redis_instance

        # Mock settings
        mock_settings = Mock()
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.redis_max_connections = 50

        with patch("src.config.settings.settings", mock_settings):
            # Verify exception is raised
            with pytest.raises(redis.ConnectionError):
                get_redis()


class TestCloseRedis:
    """Tests for close_redis function."""

    def setup_method(self):
        """Reset global redis client before each test."""
        import src.config.redis as redis_module

        redis_module._redis_client = None

    def teardown_method(self):
        """Clean up after each test."""
        import src.config.redis as redis_module

        redis_module._redis_client = None

    def test_close_redis_with_existing_client(self):
        """Test closing an existing Redis client."""
        import src.config.redis as redis_module

        # Create mock client with connection pool
        mock_pool = Mock()
        mock_client = Mock()
        mock_client.connection_pool = mock_pool
        redis_module._redis_client = mock_client

        # Close redis
        close_redis()

        # Verify
        mock_pool.disconnect.assert_called_once()
        mock_client.close.assert_called_once()
        assert redis_module._redis_client is None

    def test_close_redis_without_client(self):
        """Test closing when no client exists."""
        import src.config.redis as redis_module

        redis_module._redis_client = None

        # Should not raise exception
        close_redis()

        assert redis_module._redis_client is None
