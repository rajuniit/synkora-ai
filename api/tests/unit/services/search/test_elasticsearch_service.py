"""
Unit tests for ElasticsearchService.

tests/unit/services/database/test_elasticsearch_connector.py covers the
lower-level DatabaseConnection-based connector. This file tests the
higher-level search service used by agents.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from elasticsearch.exceptions import AuthenticationException, ConnectionError

from src.services.search.elasticsearch_service import ElasticsearchService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(
    host="localhost",
    port=9200,
    username=None,
    password=None,
    api_key=None,
    use_ssl=False,
    verify_certs=True,
):
    config = {
        "host": host,
        "port": port,
        "connection_params": {
            "api_key": api_key,
            "use_ssl": use_ssl,
            "verify_certs": verify_certs,
        },
    }
    if username:
        config["username"] = username
    if password:
        config["password"] = password

    with patch("src.services.search.elasticsearch_service.AsyncElasticsearch") as mock_cls:
        mock_cls.return_value = AsyncMock()
        svc = ElasticsearchService(config)
        svc._mock_cls = mock_cls  # kept for assertions
    return svc


def _make_search_response(hits=None, total=0, took=5):
    hits = hits or []
    return {
        "hits": {
            "hits": hits,
            "total": {"value": total},
        },
        "took": took,
    }


# ---------------------------------------------------------------------------
# __init__ — authentication path selection
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestElasticsearchServiceInit:
    def test_api_key_auth_used_when_provided(self):
        config = {
            "host": "es.example.com",
            "port": 9200,
            "connection_params": {"api_key": "my-api-key"},
        }
        with patch("src.services.search.elasticsearch_service.AsyncElasticsearch") as mock_cls:
            mock_cls.return_value = AsyncMock()
            ElasticsearchService(config)

        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["api_key"] == "my-api-key"

    def test_basic_auth_used_when_username_and_password(self):
        config = {
            "host": "es.example.com",
            "port": 9200,
            "username": "admin",
            "password": "secret",
            "connection_params": {},
        }
        with patch("src.services.search.elasticsearch_service.AsyncElasticsearch") as mock_cls:
            mock_cls.return_value = AsyncMock()
            ElasticsearchService(config)

        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["basic_auth"] == ("admin", "secret")

    def test_no_auth_when_no_credentials(self):
        config = {"host": "localhost", "port": 9200, "connection_params": {}}
        with patch("src.services.search.elasticsearch_service.AsyncElasticsearch") as mock_cls:
            mock_cls.return_value = AsyncMock()
            ElasticsearchService(config)

        call_kwargs = mock_cls.call_args.kwargs
        assert "api_key" not in call_kwargs
        assert "basic_auth" not in call_kwargs

    def test_https_url_when_use_ssl_true(self):
        config = {
            "host": "myhost",
            "port": 9243,
            "connection_params": {"use_ssl": True},
        }
        with patch("src.services.search.elasticsearch_service.AsyncElasticsearch") as mock_cls:
            mock_cls.return_value = AsyncMock()
            ElasticsearchService(config)

        url_arg = mock_cls.call_args.args[0][0]
        assert url_arg.startswith("https://")

    def test_http_url_when_use_ssl_false(self):
        config = {
            "host": "myhost",
            "port": 9200,
            "connection_params": {"use_ssl": False},
        }
        with patch("src.services.search.elasticsearch_service.AsyncElasticsearch") as mock_cls:
            mock_cls.return_value = AsyncMock()
            ElasticsearchService(config)

        url_arg = mock_cls.call_args.args[0][0]
        assert url_arg.startswith("http://")

    def test_default_port_is_9200(self):
        config = {"host": "localhost", "connection_params": {}}
        with patch("src.services.search.elasticsearch_service.AsyncElasticsearch") as mock_cls:
            mock_cls.return_value = AsyncMock()
            svc = ElasticsearchService(config)

        assert svc.port == 9200

    def test_verify_certs_passed_to_client(self):
        config = {
            "host": "localhost",
            "port": 9200,
            "connection_params": {"verify_certs": False},
        }
        with patch("src.services.search.elasticsearch_service.AsyncElasticsearch") as mock_cls:
            mock_cls.return_value = AsyncMock()
            ElasticsearchService(config)

        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["verify_certs"] is False


# ---------------------------------------------------------------------------
# search — success path
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestElasticsearchServiceSearch:
    async def test_basic_search_success(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response(
            hits=[{"_index": "idx", "_id": "1", "_score": 0.9, "_source": {"msg": "hello"}}],
            total=1,
            took=3,
        ))

        result = await svc.search("idx", "hello")

        assert result["success"] is True
        assert result["total"] == 1
        assert result["took_ms"] == 3
        assert len(result["results"]) == 1
        r = result["results"][0]
        assert r["index"] == "idx"
        assert r["id"] == "1"
        assert r["score"] == 0.9
        assert r["source"] == {"msg": "hello"}

    async def test_empty_results(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        result = await svc.search("idx", "missing")

        assert result["success"] is True
        assert result["total"] == 0
        assert result["results"] == []

    async def test_size_capped_at_100(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        await svc.search("idx", "q", size=500)

        call_body = svc.client.search.call_args.kwargs["body"]
        assert call_body["size"] == 100

    async def test_size_under_100_not_capped(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        await svc.search("idx", "q", size=20)

        call_body = svc.client.search.call_args.kwargs["body"]
        assert call_body["size"] == 20

    async def test_from_offset_sent(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        await svc.search("idx", "q", from_=50)

        call_body = svc.client.search.call_args.kwargs["body"]
        assert call_body["from"] == 50

    async def test_index_pattern_sent(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        await svc.search("slack_messages_*", "q")

        assert svc.client.search.call_args.kwargs["index"] == "slack_messages_*"

    async def test_total_as_integer_handled(self):
        """Older ES versions return total as an int, not a dict."""
        svc = _make_service()
        svc.client.search = AsyncMock(return_value={
            "hits": {"hits": [], "total": 42},
            "took": 1,
        })

        result = await svc.search("idx", "q")

        assert result["total"] == 42


# ---------------------------------------------------------------------------
# search — filters
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestElasticsearchServiceSearchFilters:
    async def test_date_range_filter_gte_added(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        await svc.search("idx", "q", filters={
            "date_range": {"field": "created_at", "gte": "2024-01-01"}
        })

        body = svc.client.search.call_args.kwargs["body"]
        filter_clauses = body["query"]["bool"]["filter"]
        range_filter = next(f for f in filter_clauses if "range" in f)
        assert range_filter["range"]["created_at"]["gte"] == "2024-01-01"

    async def test_date_range_filter_lte_added(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        await svc.search("idx", "q", filters={
            "date_range": {"field": "ts", "lte": "2024-12-31"}
        })

        body = svc.client.search.call_args.kwargs["body"]
        filter_clauses = body["query"]["bool"]["filter"]
        range_filter = next(f for f in filter_clauses if "range" in f)
        assert range_filter["range"]["ts"]["lte"] == "2024-12-31"

    async def test_term_filters_added(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        await svc.search("idx", "q", filters={
            "term_filters": {"status": "active", "tenant_id": "t1"}
        })

        body = svc.client.search.call_args.kwargs["body"]
        filter_clauses = body["query"]["bool"]["filter"]
        term_fields = {list(f["term"].keys())[0] for f in filter_clauses if "term" in f}
        assert "status" in term_fields
        assert "tenant_id" in term_fields

    async def test_no_filters_no_filter_clause(self):
        svc = _make_service()
        svc.client.search = AsyncMock(return_value=_make_search_response())

        await svc.search("idx", "q")

        body = svc.client.search.call_args.kwargs["body"]
        assert "filter" not in body["query"]["bool"]


# ---------------------------------------------------------------------------
# search — error handling
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestElasticsearchServiceSearchErrors:
    async def test_connection_error_returns_error_dict(self):
        svc = _make_service()
        svc.client.search = AsyncMock(side_effect=ConnectionError("refused"))

        result = await svc.search("idx", "q")

        assert result["success"] is False
        assert "Connection error" in result["error"]
        assert result["results"] == []

    async def test_auth_error_returns_error_dict(self):
        svc = _make_service()

        class _FakeAuthError(AuthenticationException):
            # Override read-only properties from ApiError
            error = "security_exception"
            info = {}

            def __init__(self):
                Exception.__init__(self, "bad creds")
                self.body = None
                meta = MagicMock()
                meta.status = 401
                self.meta = meta

        svc.client.search = AsyncMock(side_effect=_FakeAuthError())

        result = await svc.search("idx", "q")

        assert result["success"] is False
        assert "Authentication" in result["error"]

    async def test_generic_exception_returns_error_dict(self):
        svc = _make_service()
        svc.client.search = AsyncMock(side_effect=RuntimeError("unexpected"))

        result = await svc.search("idx", "q")

        assert result["success"] is False
        assert "unexpected" in result["error"]


# ---------------------------------------------------------------------------
# get_indices
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestElasticsearchServiceGetIndices:
    async def test_returns_sorted_index_names(self):
        svc = _make_service()
        svc.client.indices = MagicMock()
        svc.client.indices.get_alias = AsyncMock(return_value={
            "logs-2024": {},
            "logs-2023": {},
            "metrics": {},
        })

        result = await svc.get_indices()

        assert result == ["logs-2023", "logs-2024", "metrics"]

    async def test_exception_returns_empty_list(self):
        svc = _make_service()
        svc.client.indices = MagicMock()
        svc.client.indices.get_alias = AsyncMock(side_effect=ConnectionError("down"))

        result = await svc.get_indices()

        assert result == []


# ---------------------------------------------------------------------------
# get_index_stats
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestElasticsearchServiceGetIndexStats:
    async def test_returns_stats_dict(self):
        svc = _make_service()
        svc.client.indices = MagicMock()
        svc.client.indices.stats = AsyncMock(return_value={
            "_all": {
                "total": {
                    "docs": {"count": 500},
                    "store": {"size_in_bytes": 102400},
                }
            },
            "indices": {"logs-2024": {}, "logs-2023": {}},
        })

        result = await svc.get_index_stats("logs-*")

        assert result["success"] is True
        assert result["document_count"] == 500
        assert result["size_bytes"] == 102400
        assert set(result["indices"]) == {"logs-2024", "logs-2023"}

    async def test_exception_returns_error_dict(self):
        svc = _make_service()
        svc.client.indices = MagicMock()
        svc.client.indices.stats = AsyncMock(side_effect=RuntimeError("index not found"))

        result = await svc.get_index_stats("nonexistent-*")

        assert result["success"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestElasticsearchServiceTestConnection:
    async def test_success_returns_version(self):
        svc = _make_service()
        svc.client.info = AsyncMock(return_value={
            "version": {"number": "8.11.0"},
            "cluster_name": "my-cluster",
        })

        result = await svc.test_connection()

        assert result["success"] is True
        assert result["version"] == "8.11.0"
        assert result["cluster_name"] == "my-cluster"
        assert "8.11.0" in result["message"]

    async def test_connection_error_returns_failure(self):
        svc = _make_service()
        svc.client.info = AsyncMock(side_effect=ConnectionError("refused"))

        result = await svc.test_connection()

        assert result["success"] is False
        assert "Connection failed" in result["message"]

    async def test_auth_error_returns_failure(self):
        svc = _make_service()

        class _FakeAuthError(AuthenticationException):
            # Override read-only properties from ApiError
            error = "security_exception"
            info = {}

            def __init__(self):
                Exception.__init__(self, "401 unauthorized")
                self.body = None
                meta = MagicMock()
                meta.status = 401
                self.meta = meta

        svc.client.info = AsyncMock(side_effect=_FakeAuthError())

        result = await svc.test_connection()

        assert result["success"] is False
        assert "Authentication" in result["message"]

    async def test_generic_exception_returns_failure(self):
        svc = _make_service()
        svc.client.info = AsyncMock(side_effect=RuntimeError("timeout"))

        result = await svc.test_connection()

        assert result["success"] is False
        assert "failed" in result["message"].lower()


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestElasticsearchServiceClose:
    async def test_close_calls_client_close(self):
        svc = _make_service()
        svc.client.close = AsyncMock()

        await svc.close()

        svc.client.close.assert_called_once()

    async def test_close_swallows_exception(self):
        svc = _make_service()
        svc.client.close = AsyncMock(side_effect=RuntimeError("already closed"))

        # Should not raise
        await svc.close()
