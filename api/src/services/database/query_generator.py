"""Query generation and validation service for database operations."""

import logging
import re
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

# SECURITY: Maximum allowed values to prevent DoS and injection
MAX_LIMIT = 10000
MAX_OFFSET = 1000000


class QueryType(StrEnum):
    """Supported query types."""

    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    COUNT = "COUNT"
    AGGREGATE = "AGGREGATE"


class SQLQueryBuilder:
    """
    SQL query builder with validation and sanitization.

    Provides safe query construction for PostgreSQL, MySQL, and other SQL databases.
    Prevents SQL injection and validates query structure.
    """

    # Allowed SQL keywords for SELECT queries
    ALLOWED_KEYWORDS = {
        "SELECT",
        "FROM",
        "WHERE",
        "JOIN",
        "LEFT",
        "RIGHT",
        "INNER",
        "OUTER",
        "ON",
        "AND",
        "OR",
        "NOT",
        "IN",
        "LIKE",
        "BETWEEN",
        "IS",
        "NULL",
        "ORDER",
        "BY",
        "GROUP",
        "HAVING",
        "LIMIT",
        "OFFSET",
        "AS",
        "DISTINCT",
        "COUNT",
        "SUM",
        "AVG",
        "MIN",
        "MAX",
        "ASC",
        "DESC",
    }

    # Dangerous keywords that should be blocked
    DANGEROUS_KEYWORDS = {
        "DROP",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
        "SHUTDOWN",
        "KILL",
    }

    def __init__(self, max_results: int = 1000):
        """
        Initialize SQL query builder.

        Args:
            max_results: Maximum number of results to return
        """
        self.max_results = max_results

    def validate_query(self, query: str) -> tuple[bool, str | None]:
        """
        Validate SQL query for safety and correctness.

        Args:
            query: SQL query string

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for dangerous keywords
        query_upper = query.upper()
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False, f"Dangerous keyword '{keyword}' not allowed"

        # Check for multiple statements (prevent SQL injection)
        if ";" in query.strip().rstrip(";"):
            return False, "Multiple statements not allowed"

        # Check for comments (can be used for injection)
        if "--" in query or "/*" in query or "*/" in query:
            return False, "Comments not allowed in queries"

        # Validate query starts with SELECT
        if not query_upper.strip().startswith("SELECT"):
            return False, "Only SELECT queries are allowed"

        return True, None

    def sanitize_identifier(self, identifier: str) -> str:
        """
        Sanitize table/column identifier.

        Args:
            identifier: Table or column name

        Returns:
            Sanitized identifier
        """
        # Remove any non-alphanumeric characters except underscore and dot
        sanitized = re.sub(r"[^\w.]", "", identifier)
        return sanitized

    def build_select(
        self,
        table: str,
        columns: list[str] | None = None,
        where: dict[str, Any] | None = None,
        order_by: list[tuple[str, str]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> str:
        """
        Build a safe SELECT query.

        Args:
            table: Table name
            columns: List of column names (None for *)
            where: Dictionary of column: value conditions
            order_by: List of (column, direction) tuples
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            SQL query string
        """
        # Sanitize table name
        table = self.sanitize_identifier(table)

        # Build column list
        if columns:
            col_list = ", ".join([self.sanitize_identifier(col) for col in columns])
        else:
            col_list = "*"

        query = f"SELECT {col_list} FROM {table}"

        # Add WHERE clause
        if where:
            conditions = []
            for col, val in where.items():
                col = self.sanitize_identifier(col)
                if val is None:
                    conditions.append(f"{col} IS NULL")
                elif isinstance(val, (list, tuple)):
                    # IN clause
                    placeholders = ", ".join(["%s"] * len(val))
                    conditions.append(f"{col} IN ({placeholders})")
                else:
                    conditions.append(f"{col} = %s")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        # Add ORDER BY clause
        if order_by:
            order_parts = []
            for col, direction in order_by:
                col = self.sanitize_identifier(col)
                direction = direction.upper()
                if direction not in ("ASC", "DESC"):
                    direction = "ASC"
                order_parts.append(f"{col} {direction}")

            if order_parts:
                query += " ORDER BY " + ", ".join(order_parts)

        # Add LIMIT clause
        # SECURITY: Validate limit is an integer within bounds
        if limit is None:
            limit = self.max_results
        else:
            if not isinstance(limit, int) or limit < 1:
                limit = self.max_results
            else:
                limit = min(limit, self.max_results, MAX_LIMIT)

        query += f" LIMIT {int(limit)}"

        # Add OFFSET clause
        # SECURITY: Validate offset is an integer within bounds
        if offset is not None:
            if isinstance(offset, int) and 0 <= offset <= MAX_OFFSET:
                query += f" OFFSET {int(offset)}"

        return query

    def build_count(self, table: str, where: dict[str, Any] | None = None) -> str:
        """
        Build a COUNT query.

        Args:
            table: Table name
            where: Dictionary of column: value conditions

        Returns:
            SQL query string
        """
        table = self.sanitize_identifier(table)
        query = f"SELECT COUNT(*) as count FROM {table}"

        if where:
            conditions = []
            for col, val in where.items():
                col = self.sanitize_identifier(col)
                if val is None:
                    conditions.append(f"{col} IS NULL")
                elif isinstance(val, (list, tuple)):
                    placeholders = ", ".join(["%s"] * len(val))
                    conditions.append(f"{col} IN ({placeholders})")
                else:
                    conditions.append(f"{col} = %s")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        return query

    def extract_parameters(self, where: dict[str, Any] | None = None) -> list[Any]:
        """
        Extract parameter values from WHERE conditions.

        Args:
            where: Dictionary of column: value conditions

        Returns:
            List of parameter values
        """
        if not where:
            return []

        params = []
        for val in where.values():
            if val is None:
                continue
            elif isinstance(val, (list, tuple)):
                params.extend(val)
            else:
                params.append(val)

        return params


class ElasticsearchQueryBuilder:
    """
    Elasticsearch query builder with validation.

    Provides safe query construction for Elasticsearch.
    """

    def __init__(self, max_results: int = 1000):
        """
        Initialize Elasticsearch query builder.

        Args:
            max_results: Maximum number of results to return
        """
        self.max_results = max_results

    def build_search(
        self,
        index: str,
        query: dict[str, Any] | None = None,
        filters: list[dict[str, Any]] | None = None,
        sort: list[dict[str, Any]] | None = None,
        size: int | None = None,
        from_: int | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Build an Elasticsearch search query.

        Args:
            index: Index name
            query: Query DSL dictionary
            filters: List of filter dictionaries
            sort: List of sort dictionaries
            size: Maximum number of results
            from_: Number of results to skip
            fields: List of fields to return

        Returns:
            Elasticsearch query dictionary
        """
        es_query: dict[str, Any] = {}

        # Build query
        if query or filters:
            bool_query: dict[str, Any] = {"bool": {}}

            if query:
                bool_query["bool"]["must"] = query

            if filters:
                bool_query["bool"]["filter"] = filters

            es_query["query"] = bool_query
        else:
            es_query["query"] = {"match_all": {}}

        # Add sort
        if sort:
            es_query["sort"] = sort

        # Add size
        if size is None:
            size = self.max_results
        else:
            size = min(size, self.max_results)

        es_query["size"] = size

        # Add from
        if from_:
            es_query["from"] = from_

        # Add fields
        if fields:
            es_query["_source"] = fields

        return es_query

    def build_match_query(self, field: str, value: str) -> dict[str, Any]:
        """
        Build a match query.

        Args:
            field: Field name
            value: Search value

        Returns:
            Match query dictionary
        """
        return {"match": {field: value}}

    def build_term_query(self, field: str, value: Any) -> dict[str, Any]:
        """
        Build a term query (exact match).

        Args:
            field: Field name
            value: Search value

        Returns:
            Term query dictionary
        """
        return {"term": {field: value}}

    def build_range_query(
        self, field: str, gte: Any | None = None, lte: Any | None = None, gt: Any | None = None, lt: Any | None = None
    ) -> dict[str, Any]:
        """
        Build a range query.

        Args:
            field: Field name
            gte: Greater than or equal to
            lte: Less than or equal to
            gt: Greater than
            lt: Less than

        Returns:
            Range query dictionary
        """
        range_params = {}
        if gte is not None:
            range_params["gte"] = gte
        if lte is not None:
            range_params["lte"] = lte
        if gt is not None:
            range_params["gt"] = gt
        if lt is not None:
            range_params["lt"] = lt

        return {"range": {field: range_params}}

    def build_aggregation(self, name: str, agg_type: str, field: str, **kwargs) -> dict[str, Any]:
        """
        Build an aggregation.

        Args:
            name: Aggregation name
            agg_type: Aggregation type (terms, avg, sum, etc.)
            field: Field name
            **kwargs: Additional aggregation parameters

        Returns:
            Aggregation dictionary
        """
        return {name: {agg_type: {"field": field, **kwargs}}}


class QueryGenerator:
    """
    Main query generator service.

    Provides unified interface for generating queries across different database types.
    """

    def __init__(self, max_results: int = 1000):
        """
        Initialize query generator.

        Args:
            max_results: Maximum number of results to return
        """
        self.sql_builder = SQLQueryBuilder(max_results=max_results)
        self.es_builder = ElasticsearchQueryBuilder(max_results=max_results)

    def generate_sql_query(
        self,
        table: str,
        columns: list[str] | None = None,
        where: dict[str, Any] | None = None,
        order_by: list[tuple[str, str]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[str, list[Any]]:
        """
        Generate a SQL query with parameters.

        Args:
            table: Table name
            columns: List of column names
            where: WHERE conditions
            order_by: ORDER BY clauses
            limit: LIMIT value
            offset: OFFSET value

        Returns:
            Tuple of (query_string, parameters)
        """
        query = self.sql_builder.build_select(
            table=table, columns=columns, where=where, order_by=order_by, limit=limit, offset=offset
        )

        # Validate query
        is_valid, error = self.sql_builder.validate_query(query)
        if not is_valid:
            raise ValueError(f"Invalid query: {error}")

        # Extract parameters
        params = self.sql_builder.extract_parameters(where)

        return query, params

    def generate_elasticsearch_query(
        self,
        index: str,
        query: dict[str, Any] | None = None,
        filters: list[dict[str, Any]] | None = None,
        sort: list[dict[str, Any]] | None = None,
        size: int | None = None,
        from_: int | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate an Elasticsearch query.

        Args:
            index: Index name
            query: Query DSL
            filters: Filter clauses
            sort: Sort clauses
            size: Result size
            from_: Result offset
            fields: Fields to return

        Returns:
            Elasticsearch query dictionary
        """
        return self.es_builder.build_search(
            index=index, query=query, filters=filters, sort=sort, size=size, from_=from_, fields=fields
        )
