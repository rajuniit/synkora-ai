"""Unit tests for OpenAPIParser."""

import pytest

from src.services.custom_tools.openapi_parser import OpenAPIParser


def _minimal_schema(paths: dict | None = None, servers: list | None = None) -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0", "description": "A test API"},
        "servers": servers or [{"url": "https://api.example.com"}],
        "paths": paths or {},
    }


def _pet_schema() -> dict:
    return _minimal_schema(
        paths={
            "/pets": {
                "get": {
                    "operationId": "listPets",
                    "summary": "List all pets",
                    "description": "Returns all pets",
                    "parameters": [
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "OK"}},
                    "tags": ["pets"],
                },
                "post": {
                    "operationId": "createPet",
                    "summary": "Create a pet",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "properties": {"name": {"type": "string"}}}
                            }
                        },
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/pets/{petId}": {
                "get": {
                    "operationId": "getPetById",
                    "summary": "Get a pet",
                    "parameters": [{"name": "petId", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}},
                }
            },
        }
    )


@pytest.mark.unit
class TestServerUrlExtraction:
    def test_extracts_first_server_url(self):
        schema = _minimal_schema(servers=[{"url": "https://api.example.com"}])
        parser = OpenAPIParser(schema)
        assert parser.server_url == "https://api.example.com"

    def test_multiple_servers_uses_first(self):
        schema = _minimal_schema(servers=[{"url": "https://prod.example.com"}, {"url": "https://staging.example.com"}])
        parser = OpenAPIParser(schema)
        assert parser.server_url == "https://prod.example.com"

    def test_no_servers_returns_empty_string(self):
        schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [],
            "paths": {},
        }
        parser = OpenAPIParser(schema)
        assert parser.server_url == ""

    def test_override_server_url(self):
        schema = _minimal_schema(servers=[{"url": "https://api.example.com"}])
        parser = OpenAPIParser(schema, server_url="https://custom.example.com")
        assert parser.server_url == "https://custom.example.com"


@pytest.mark.unit
class TestGetAvailableOperations:
    def setup_method(self):
        self.parser = OpenAPIParser(_pet_schema())

    def test_returns_correct_count(self):
        ops = self.parser.get_available_operations()
        assert len(ops) == 3

    def test_operation_has_required_fields(self):
        ops = self.parser.get_available_operations()
        for op in ops:
            assert "operation_id" in op
            assert "method" in op
            assert "path" in op
            assert "parameters" in op

    def test_operation_ids_present(self):
        ops = self.parser.get_available_operations()
        ids = {op["operation_id"] for op in ops}
        assert "listPets" in ids
        assert "createPet" in ids
        assert "getPetById" in ids

    def test_methods_are_uppercase(self):
        ops = self.parser.get_available_operations()
        for op in ops:
            assert op["method"] == op["method"].upper()

    def test_empty_paths_returns_empty(self):
        parser = OpenAPIParser(_minimal_schema(paths={}))
        assert parser.get_available_operations() == []

    def test_operation_without_operation_id_gets_generated_id(self):
        schema = _minimal_schema(paths={"/things": {"get": {"responses": {"200": {"description": "OK"}}}}})
        parser = OpenAPIParser(schema)
        ops = parser.get_available_operations()
        assert len(ops) == 1
        assert ops[0]["operation_id"] == "get__things"

    def test_tags_included(self):
        ops = self.parser.get_available_operations()
        list_op = next(op for op in ops if op["operation_id"] == "listPets")
        assert list_op["tags"] == ["pets"]


@pytest.mark.unit
class TestParseParameters:
    def setup_method(self):
        self.parser = OpenAPIParser(_pet_schema())

    def test_query_parameter_parsed(self):
        ops = self.parser.get_available_operations()
        list_op = next(op for op in ops if op["operation_id"] == "listPets")
        params = list_op["parameters"]
        assert len(params) == 1
        assert params[0]["name"] == "limit"
        assert params[0]["in"] == "query"
        assert params[0]["required"] is False

    def test_path_parameter_parsed(self):
        ops = self.parser.get_available_operations()
        get_op = next(op for op in ops if op["operation_id"] == "getPetById")
        params = get_op["parameters"]
        assert any(p["name"] == "petId" and p["in"] == "path" and p["required"] is True for p in params)

    def test_path_level_params_inherited(self):
        schema = _minimal_schema(
            paths={
                "/items/{id}": {
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "get": {
                        "operationId": "getItem",
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            }
        )
        parser = OpenAPIParser(schema)
        ops = parser.get_available_operations()
        assert any(p["name"] == "id" for p in ops[0]["parameters"])

    def test_operation_param_overrides_path_param(self):
        schema = _minimal_schema(
            paths={
                "/items/{id}": {
                    "parameters": [{"name": "id", "in": "path", "required": False, "schema": {"type": "string"}}],
                    "get": {
                        "operationId": "getItem",
                        "parameters": [
                            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                        ],
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            }
        )
        parser = OpenAPIParser(schema)
        ops = parser.get_available_operations()
        id_param = next(p for p in ops[0]["parameters"] if p["name"] == "id")
        assert id_param["required"] is True


@pytest.mark.unit
class TestParseRequestBody:
    def setup_method(self):
        self.parser = OpenAPIParser(_pet_schema())

    def test_request_body_parsed(self):
        ops = self.parser.get_available_operations()
        create_op = next(op for op in ops if op["operation_id"] == "createPet")
        rb = create_op["request_body"]
        assert rb is not None
        assert rb["required"] is True
        assert "schema" in rb

    def test_no_request_body_returns_none(self):
        ops = self.parser.get_available_operations()
        list_op = next(op for op in ops if op["operation_id"] == "listPets")
        assert list_op["request_body"] is None

    def test_non_json_content_type_used(self):
        schema = _minimal_schema(
            paths={
                "/upload": {
                    "post": {
                        "operationId": "upload",
                        "requestBody": {
                            "content": {"multipart/form-data": {"schema": {"type": "object"}}},
                            "required": True,
                        },
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            }
        )
        parser = OpenAPIParser(schema)
        ops = parser.get_available_operations()
        rb = ops[0]["request_body"]
        assert rb is not None


@pytest.mark.unit
class TestResolveRef:
    def setup_method(self):
        schema = _minimal_schema()
        schema["components"] = {
            "schemas": {
                "Pet": {"type": "object", "properties": {"name": {"type": "string"}}},
                "Error": {"type": "object"},
            }
        }
        self.parser = OpenAPIParser(schema)

    def test_resolves_local_ref(self):
        result = self.parser._resolve_ref("#/components/schemas/Pet")
        assert result["type"] == "object"
        assert "name" in result["properties"]

    def test_external_ref_returns_empty(self):
        result = self.parser._resolve_ref("https://external.example.com/schema.json")
        assert result == {}

    def test_missing_ref_returns_empty(self):
        result = self.parser._resolve_ref("#/components/schemas/NonExistent")
        assert result == {}


@pytest.mark.unit
class TestGetToolDefinition:
    def setup_method(self):
        self.parser = OpenAPIParser(_pet_schema())

    def test_returns_operation_by_id(self):
        result = self.parser.get_tool_definition("listPets")
        assert result is not None
        assert result["operation_id"] == "listPets"

    def test_returns_none_for_unknown_id(self):
        result = self.parser.get_tool_definition("doesNotExist")
        assert result is None


@pytest.mark.unit
class TestBuildRequestUrl:
    def setup_method(self):
        self.parser = OpenAPIParser(_pet_schema())

    def test_builds_url_with_path_params(self):
        op = {"path": "/pets/{petId}"}
        url = self.parser.build_request_url(op, {"petId": "123"})
        assert "123" in url
        assert "{petId}" not in url

    def test_builds_url_without_path_params(self):
        op = {"path": "/pets"}
        url = self.parser.build_request_url(op, {})
        assert url.endswith("/pets")


@pytest.mark.unit
class TestValidateParameters:
    def setup_method(self):
        self.parser = OpenAPIParser(_pet_schema())

    def test_valid_required_param_present(self):
        op = {
            "parameters": [{"name": "petId", "required": True, "in": "path"}],
            "request_body": None,
        }
        valid, errors = self.parser.validate_parameters(op, {"petId": "abc"})
        assert valid is True
        assert errors == []

    def test_missing_required_param_returns_error(self):
        op = {
            "parameters": [{"name": "petId", "required": True, "in": "path"}],
            "request_body": None,
        }
        valid, errors = self.parser.validate_parameters(op, {})
        assert valid is False
        assert any("petId" in e for e in errors)

    def test_optional_param_missing_is_valid(self):
        op = {
            "parameters": [{"name": "limit", "required": False, "in": "query"}],
            "request_body": None,
        }
        valid, errors = self.parser.validate_parameters(op, {})
        assert valid is True

    def test_required_body_missing_returns_error(self):
        op = {
            "parameters": [],
            "request_body": {"required": True, "schema": {}},
        }
        valid, errors = self.parser.validate_parameters(op, {})
        assert valid is False
        assert any("body" in e.lower() for e in errors)


@pytest.mark.unit
class TestGetSchemaInfo:
    def test_returns_api_metadata(self):
        parser = OpenAPIParser(_pet_schema())
        info = parser.get_schema_info()
        assert info["title"] == "Test API"
        assert info["version"] == "1.0.0"
        assert info["server_url"] == "https://api.example.com"
        assert info["openapi_version"] == "3.0.0"
        assert info["operation_count"] == 3

    def test_missing_info_uses_defaults(self):
        schema = {"openapi": "3.1.0", "paths": {}}
        parser = OpenAPIParser(schema)
        info = parser.get_schema_info()
        assert info["title"] == "Unknown API"
        assert info["version"] == "1.0.0"
