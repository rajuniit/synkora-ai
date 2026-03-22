import pytest

from src.services.database.query_generator import ElasticsearchQueryBuilder, QueryGenerator, SQLQueryBuilder


class TestSQLQueryBuilder:
    @pytest.fixture
    def builder(self):
        return SQLQueryBuilder(max_results=100)

    def test_validate_query_valid(self, builder):
        valid, error = builder.validate_query("SELECT * FROM users")
        assert valid is True
        assert error is None

    def test_validate_query_dangerous(self, builder):
        valid, error = builder.validate_query("DROP TABLE users")
        assert valid is False
        assert "Dangerous keyword" in error

    def test_validate_query_multiple_statements(self, builder):
        valid, error = builder.validate_query("SELECT * FROM users; SELECT * FROM other")
        assert valid is False
        assert "Multiple statements" in error

    def test_validate_query_comments(self, builder):
        valid, error = builder.validate_query("SELECT * FROM users -- comment")
        assert valid is False
        assert "Comments not allowed" in error

    def test_validate_query_not_select(self, builder):
        valid, error = builder.validate_query("INSERT INTO users VALUES (1)")
        assert valid is False
        assert "Only SELECT queries" in error

    def test_sanitize_identifier(self, builder):
        assert builder.sanitize_identifier("table_name") == "table_name"
        assert builder.sanitize_identifier("table.column") == "table.column"
        assert builder.sanitize_identifier("invalid;name") == "invalidname"
        assert builder.sanitize_identifier("drop table") == "droptable"

    def test_build_select_basic(self, builder):
        query = builder.build_select("users")
        assert query == "SELECT * FROM users LIMIT 100"

    def test_build_select_full(self, builder):
        query = builder.build_select(
            table="users",
            columns=["id", "name"],
            where={"age": 20, "status": ["active", "pending"], "role": None},
            order_by=[("name", "ASC"), ("age", "DESC")],
            limit=10,
            offset=5,
        )

        assert "SELECT id, name FROM users" in query
        assert "WHERE" in query
        assert "age = %s" in query
        assert "status IN (%s, %s)" in query
        assert "role IS NULL" in query
        assert "ORDER BY name ASC, age DESC" in query
        assert "LIMIT 10" in query
        assert "OFFSET 5" in query

    def test_build_select_limit_override(self, builder):
        # Override higher than max results
        query = builder.build_select("users", limit=200)
        assert "LIMIT 100" in query

        # Override lower than max results
        query = builder.build_select("users", limit=50)
        assert "LIMIT 50" in query

    def test_build_count(self, builder):
        query = builder.build_count("users", where={"status": "active"})
        assert query == "SELECT COUNT(*) as count FROM users WHERE status = %s"

    def test_extract_parameters(self, builder):
        where = {"age": 20, "status": ["active", "pending"], "role": None}
        params = builder.extract_parameters(where)
        assert params == [20, "active", "pending"]


class TestElasticsearchQueryBuilder:
    @pytest.fixture
    def builder(self):
        return ElasticsearchQueryBuilder(max_results=100)

    def test_build_search_basic(self, builder):
        query = builder.build_search("index_name")
        assert query["query"] == {"match_all": {}}
        assert query["size"] == 100

    def test_build_search_full(self, builder):
        query_dsl = {"match": {"field": "value"}}
        filters = [{"term": {"status": "active"}}]
        sort = [{"field": "asc"}]

        result = builder.build_search(
            index="index_name", query=query_dsl, filters=filters, sort=sort, size=10, from_=5, fields=["field1"]
        )

        assert result["query"]["bool"]["must"] == query_dsl
        assert result["query"]["bool"]["filter"] == filters
        assert result["sort"] == sort
        assert result["size"] == 10
        assert result["from"] == 5
        assert result["_source"] == ["field1"]

    def test_build_match_query(self, builder):
        query = builder.build_match_query("field", "value")
        assert query == {"match": {"field": "value"}}

    def test_build_term_query(self, builder):
        query = builder.build_term_query("field", "value")
        assert query == {"term": {"field": "value"}}

    def test_build_range_query(self, builder):
        query = builder.build_range_query("field", gte=10, lt=20)
        assert query == {"range": {"field": {"gte": 10, "lt": 20}}}

    def test_build_aggregation(self, builder):
        agg = builder.build_aggregation("my_agg", "terms", "field", size=10)
        assert agg == {"my_agg": {"terms": {"field": "field", "size": 10}}}


class TestQueryGenerator:
    @pytest.fixture
    def generator(self):
        return QueryGenerator(max_results=100)

    def test_generate_sql_query(self, generator):
        query, params = generator.generate_sql_query(table="users", where={"id": 1})
        assert "SELECT * FROM users" in query
        assert "WHERE id = %s" in query
        assert params == [1]

    def test_generate_sql_query_invalid(self, generator):
        # Mock validation failure
        generator.sql_builder.validate_query = lambda x: (False, "Error")
        with pytest.raises(ValueError, match="Invalid query"):
            generator.generate_sql_query("table")

    def test_generate_elasticsearch_query(self, generator):
        # Case 1: Custom query
        query = generator.generate_elasticsearch_query(index="users", query={"match": {"name": "test"}})
        assert query["query"]["bool"]["must"] == {"match": {"name": "test"}}

        # Case 2: No query (default match_all)
        query = generator.generate_elasticsearch_query(index="users")
        assert query["query"] == {"match_all": {}}
