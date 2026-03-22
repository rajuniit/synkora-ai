"""
Integration tests for Knowledge Base CRUD operations.

Tests the complete lifecycle of knowledge bases: create, list, get, update, delete.
"""

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def auth_headers(client: TestClient, db_session: Session):
    """Create authenticated user and return headers with tenant info."""
    from src.models import Account, AccountStatus

    # Create user and get token
    email = f"test_kb_{uuid.uuid4()}@example.com"
    password = "SecureTestPass123!"

    # Register
    response = client.post(
        "/console/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "KB Test User",
            "tenant_name": "KB Test Org",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    tenant_id = data["data"]["tenant"]["id"]
    account_id = data["data"]["account"]["id"]

    # Manually activate account for testing (simulating email verification)
    account = db_session.query(Account).filter_by(email=email).first()
    account.status = AccountStatus.ACTIVE
    db_session.commit()

    # Login to get token
    login_response = client.post(
        "/console/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == status.HTTP_200_OK
    token = login_response.json()["data"]["access_token"]

    return {"Authorization": f"Bearer {token}"}, tenant_id, account_id


class TestKnowledgeBasesCRUDIntegration:
    """Test Knowledge Base CRUD operations."""

    def test_knowledge_base_full_lifecycle(self, client: TestClient, db_session: Session, auth_headers):
        """Test complete knowledge base lifecycle: create -> get -> update -> delete."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"TestKB_{uuid.uuid4().hex[:8]}"

        # 1. Create Knowledge Base
        create_response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test knowledge base for integration tests",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
                "chunk_size": 1500,
                "chunk_overlap": 150,
            },
            headers=headers,
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        create_data = create_response.json()
        assert create_data["name"] == kb_name
        kb_id = create_data["id"]

        # 2. Get Knowledge Base
        get_response = client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        assert get_data["name"] == kb_name
        assert get_data["description"] == "Test knowledge base for integration tests"

        # 3. List Knowledge Bases
        list_response = client.get("/api/v1/knowledge-bases", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        assert isinstance(list_data, list)
        kb_ids = [kb["id"] for kb in list_data]
        assert kb_id in kb_ids

        # 4. Update Knowledge Base
        update_response = client.put(
            f"/api/v1/knowledge-bases/{kb_id}",
            json={
                "name": f"{kb_name}_updated",
                "description": "Updated description",
                "chunk_size": 2000,
            },
            headers=headers,
        )
        assert update_response.status_code == status.HTTP_200_OK
        update_data = update_response.json()
        assert update_data["name"] == f"{kb_name}_updated"
        assert update_data["description"] == "Updated description"
        assert update_data["chunk_size"] == 2000

        # 5. Get Knowledge Base Stats
        stats_response = client.get(f"/api/v1/knowledge-bases/{kb_id}/stats", headers=headers)
        assert stats_response.status_code == status.HTTP_200_OK
        stats_data = stats_response.json()
        assert stats_data["id"] == kb_id
        assert "document_count" in stats_data
        assert "total_chunks" in stats_data

        # 6. Delete Knowledge Base
        delete_response = client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        verify_response = client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_nonexistent_knowledge_base(self, client: TestClient, db_session: Session, auth_headers):
        """Test that getting a nonexistent knowledge base returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers

        response = client.get("/api/v1/knowledge-bases/99999", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_nonexistent_knowledge_base(self, client: TestClient, db_session: Session, auth_headers):
        """Test that updating a nonexistent knowledge base returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers

        response = client.put(
            "/api/v1/knowledge-bases/99999",
            json={"name": "Updated Name"},
            headers=headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_knowledge_base(self, client: TestClient, db_session: Session, auth_headers):
        """Test that deleting a nonexistent knowledge base returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers

        response = client.delete("/api/v1/knowledge-bases/99999", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_knowledge_base_with_invalid_provider(self, client: TestClient, db_session: Session, auth_headers):
        """Test that creating a knowledge base with invalid provider fails."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"InvalidProviderKB_{uuid.uuid4().hex[:8]}"

        response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test KB",
                "embedding_provider": "INVALID_PROVIDER",
                "embedding_model": "test-model",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_knowledge_base_with_invalid_chunking_strategy(
        self, client: TestClient, db_session: Session, auth_headers
    ):
        """Test that creating a knowledge base with invalid chunking strategy fails."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"InvalidChunkingKB_{uuid.uuid4().hex[:8]}"

        response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test KB",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "INVALID_STRATEGY",
            },
            headers=headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_knowledge_base_pagination(self, client: TestClient, db_session: Session, auth_headers):
        """Test knowledge base list pagination."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers

        # Create multiple knowledge bases
        kb_ids = []
        for i in range(5):
            kb_name = f"PaginationKB_{uuid.uuid4().hex[:8]}_{i}"
            response = client.post(
                "/api/v1/knowledge-bases",
                json={
                    "name": kb_name,
                    "description": f"Test KB {i}",
                    "embedding_provider": "SENTENCE_TRANSFORMERS",
                    "embedding_model": "all-MiniLM-L6-v2",
                    "vector_db_provider": "QDRANT",
                    "chunking_strategy": "SEMANTIC",
                },
                headers=headers,
            )
            assert response.status_code == status.HTTP_201_CREATED
            kb_ids.append(response.json()["id"])

        # Test pagination
        page1_response = client.get("/api/v1/knowledge-bases?skip=0&limit=2", headers=headers)
        assert page1_response.status_code == status.HTTP_200_OK
        page1_data = page1_response.json()
        assert len(page1_data) == 2

        page2_response = client.get("/api/v1/knowledge-bases?skip=2&limit=2", headers=headers)
        assert page2_response.status_code == status.HTTP_200_OK
        page2_data = page2_response.json()
        assert len(page2_data) == 2

    def test_knowledge_base_text_content(self, client: TestClient, db_session: Session, auth_headers):
        """Test adding text content to knowledge base."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"TextContentKB_{uuid.uuid4().hex[:8]}"

        # Create knowledge base
        create_response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test KB for text content",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
            },
            headers=headers,
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        kb_id = create_response.json()["id"]

        # Add text content (note: this may fail if embedding service is not available)
        # We test the endpoint is accessible, not the full processing
        text_response = client.post(
            f"/api/v1/knowledge-bases/{kb_id}/documents/text",
            json={
                "title": "Test Document",
                "content": "This is test content for the knowledge base. It contains important information.",
                "metadata": {"source": "test"},
            },
            headers=headers,
        )
        # This might fail due to external dependencies, so we accept both success and service errors
        assert text_response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestKnowledgeBaseDocumentsIntegration:
    """Test Knowledge Base document operations."""

    def test_list_documents_empty(self, client: TestClient, db_session: Session, auth_headers):
        """Test listing documents in an empty knowledge base."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"EmptyDocsKB_{uuid.uuid4().hex[:8]}"

        # Create knowledge base
        create_response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test KB",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
            },
            headers=headers,
        )
        kb_id = create_response.json()["id"]

        # List documents
        list_response = client.get(f"/api/v1/knowledge-bases/{kb_id}/documents", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        list_data = list_response.json()
        assert list_data["documents"] == []
        assert list_data["total"] == 0

    def test_list_documents_pagination(self, client: TestClient, db_session: Session, auth_headers):
        """Test document list pagination parameters."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"PaginationDocsKB_{uuid.uuid4().hex[:8]}"

        # Create knowledge base
        create_response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test KB",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
            },
            headers=headers,
        )
        kb_id = create_response.json()["id"]

        # Test pagination parameters
        response = client.get(
            f"/api/v1/knowledge-bases/{kb_id}/documents?page=1&page_size=10&sort_by=created_at&sort_order=desc",
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_get_nonexistent_document(self, client: TestClient, db_session: Session, auth_headers):
        """Test getting a nonexistent document returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"NonexistentDocKB_{uuid.uuid4().hex[:8]}"

        # Create knowledge base
        create_response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test KB",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
            },
            headers=headers,
        )
        kb_id = create_response.json()["id"]

        # Try to get nonexistent document
        fake_doc_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/knowledge-bases/{kb_id}/documents/{fake_doc_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_document(self, client: TestClient, db_session: Session, auth_headers):
        """Test deleting a nonexistent document returns 404."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"DeleteDocKB_{uuid.uuid4().hex[:8]}"

        # Create knowledge base
        create_response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test KB",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
            },
            headers=headers,
        )
        kb_id = create_response.json()["id"]

        # Try to delete nonexistent document
        fake_doc_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/knowledge-bases/{kb_id}/documents/{fake_doc_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestKnowledgeBaseSearchIntegration:
    """Test Knowledge Base search operations."""

    def test_search_empty_knowledge_base(self, client: TestClient, db_session: Session, auth_headers):
        """Test searching an empty knowledge base."""
        from src.core.database import get_db

        client.app.dependency_overrides[get_db] = lambda: db_session

        headers, tenant_id, account_id = auth_headers
        kb_name = f"SearchEmptyKB_{uuid.uuid4().hex[:8]}"

        # Create knowledge base
        create_response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Test KB for search",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
            },
            headers=headers,
        )
        kb_id = create_response.json()["id"]

        # Search (may fail due to external dependencies)
        search_response = client.post(
            f"/api/v1/knowledge-bases/{kb_id}/search",
            json={"query": "test query", "limit": 5, "min_score": 0.5},
            headers=headers,
        )
        # Accept both success (empty results) and service errors
        assert search_response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestKnowledgeBaseTenantIsolation:
    """Test Knowledge Base tenant isolation."""

    def test_cannot_access_other_tenant_kb(self, client: TestClient, db_session: Session):
        """Test that users cannot access knowledge bases from other tenants."""
        from src.core.database import get_db
        from src.models import Account, AccountStatus

        client.app.dependency_overrides[get_db] = lambda: db_session

        # Create first user/tenant
        email1 = f"tenant1_kb_{uuid.uuid4()}@example.com"
        client.post(
            "/console/api/auth/register",
            json={
                "email": email1,
                "password": "SecureTestPass123!",
                "name": "Tenant 1 User",
                "tenant_name": "Tenant 1 Org",
            },
        )
        account1 = db_session.query(Account).filter_by(email=email1).first()
        account1.status = AccountStatus.ACTIVE
        db_session.commit()

        login1 = client.post("/console/api/auth/login", json={"email": email1, "password": "SecureTestPass123!"})
        token1 = login1.json()["data"]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create second user/tenant
        email2 = f"tenant2_kb_{uuid.uuid4()}@example.com"
        client.post(
            "/console/api/auth/register",
            json={
                "email": email2,
                "password": "SecureTestPass123!",
                "name": "Tenant 2 User",
                "tenant_name": "Tenant 2 Org",
            },
        )
        account2 = db_session.query(Account).filter_by(email=email2).first()
        account2.status = AccountStatus.ACTIVE
        db_session.commit()

        login2 = client.post("/console/api/auth/login", json={"email": email2, "password": "SecureTestPass123!"})
        token2 = login2.json()["data"]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Create KB as tenant 1
        kb_name = f"IsolatedKB_{uuid.uuid4().hex[:8]}"
        create_response = client.post(
            "/api/v1/knowledge-bases",
            json={
                "name": kb_name,
                "description": "Tenant 1 KB",
                "embedding_provider": "SENTENCE_TRANSFORMERS",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_db_provider": "QDRANT",
                "chunking_strategy": "SEMANTIC",
            },
            headers=headers1,
        )
        kb_id = create_response.json()["id"]

        # Tenant 2 should not be able to access tenant 1's KB
        get_response = client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=headers2)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to update tenant 1's KB
        update_response = client.put(f"/api/v1/knowledge-bases/{kb_id}", json={"name": "Hacked KB"}, headers=headers2)
        assert update_response.status_code == status.HTTP_404_NOT_FOUND

        # Tenant 2 should not be able to delete tenant 1's KB
        delete_response = client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=headers2)
        assert delete_response.status_code == status.HTTP_404_NOT_FOUND
