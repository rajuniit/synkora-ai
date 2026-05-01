"""
Unit tests for KB brain SQLAlchemy models.
Verifies table names, column names, unique constraints, and relationships
without a real database connection.
"""

from sqlalchemy import UniqueConstraint

from src.models.kb_brain import KBEntity, KBRelationship, KBSyncCursor

# ---------------------------------------------------------------------------
# KBSyncCursor
# ---------------------------------------------------------------------------


class TestKBSyncCursor:
    def test_tablename(self):
        assert KBSyncCursor.__tablename__ == "kb_sync_cursors"

    def test_has_knowledge_base_id_column(self):
        cols = {c.key for c in KBSyncCursor.__table__.columns}
        assert "knowledge_base_id" in cols

    def test_has_data_source_id_column(self):
        cols = {c.key for c in KBSyncCursor.__table__.columns}
        assert "data_source_id" in cols

    def test_has_tenant_id_column(self):
        cols = {c.key for c in KBSyncCursor.__table__.columns}
        assert "tenant_id" in cols

    def test_has_cursor_type_and_value(self):
        cols = {c.key for c in KBSyncCursor.__table__.columns}
        assert "cursor_type" in cols
        assert "cursor_value" in cols

    def test_has_docs_seen(self):
        cols = {c.key for c in KBSyncCursor.__table__.columns}
        assert "docs_seen" in cols

    def test_unique_constraint_data_source_cursor_type(self):
        constraint_names = {c.name for c in KBSyncCursor.__table__.constraints if isinstance(c, UniqueConstraint)}
        assert "uq_kb_cursor_source_type" in constraint_names

    def test_repr(self):
        cursor = KBSyncCursor()
        cursor.knowledge_base_id = 1
        cursor.data_source_id = 2
        cursor.cursor_type = "since_ts"
        r = repr(cursor)
        assert "kb=1" in r
        assert "ds=2" in r
        assert "since_ts" in r


# ---------------------------------------------------------------------------
# KBEntity
# ---------------------------------------------------------------------------


class TestKBEntity:
    def test_tablename(self):
        assert KBEntity.__tablename__ == "kb_entities"

    def test_required_columns(self):
        cols = {c.key for c in KBEntity.__table__.columns}
        for col in (
            "id",
            "tenant_id",
            "knowledge_base_id",
            "entity_type",
            "canonical_name",
            "email",
            "identifiers",
            "display_names",
        ):
            assert col in cols, f"Missing column: {col}"

    def test_unique_constraint_kb_email(self):
        constraint_names = {c.name for c in KBEntity.__table__.constraints if isinstance(c, UniqueConstraint)}
        assert "uq_kb_entity_kb_email" in constraint_names

    def test_email_nullable(self):
        email_col = KBEntity.__table__.c["email"]
        assert email_col.nullable is True

    def test_has_source_relationships_relationship(self):
        assert hasattr(KBEntity, "source_relationships")

    def test_has_target_relationships_relationship(self):
        assert hasattr(KBEntity, "target_relationships")

    def test_repr(self):
        e = KBEntity()
        e.knowledge_base_id = 5
        e.entity_type = "person"
        e.canonical_name = "Alice"
        r = repr(e)
        assert "kb=5" in r
        assert "person" in r
        assert "Alice" in r


# ---------------------------------------------------------------------------
# KBRelationship
# ---------------------------------------------------------------------------


class TestKBRelationship:
    def test_tablename(self):
        assert KBRelationship.__tablename__ == "kb_relationships"

    def test_required_columns(self):
        cols = {c.key for c in KBRelationship.__table__.columns}
        for col in (
            "id",
            "tenant_id",
            "knowledge_base_id",
            "source_entity_id",
            "target_entity_id",
            "source_doc_id",
            "relation_type",
            "rel_metadata",
            "occurred_at",
        ):
            assert col in cols, f"Missing column: {col}"

    def test_source_entity_nullable(self):
        col = KBRelationship.__table__.c["source_entity_id"]
        assert col.nullable is True

    def test_target_entity_nullable(self):
        col = KBRelationship.__table__.c["target_entity_id"]
        assert col.nullable is True

    def test_source_doc_nullable(self):
        col = KBRelationship.__table__.c["source_doc_id"]
        assert col.nullable is True

    def test_has_source_entity_relationship(self):
        assert hasattr(KBRelationship, "source_entity")

    def test_has_target_entity_relationship(self):
        assert hasattr(KBRelationship, "target_entity")

    def test_repr(self):
        r = KBRelationship()
        r.knowledge_base_id = 7
        r.relation_type = "authored"
        result = repr(r)
        assert "kb=7" in result
        assert "authored" in result


# ---------------------------------------------------------------------------
# Foreign key targets
# ---------------------------------------------------------------------------


class TestForeignKeys:
    def test_kb_sync_cursor_kb_fk_targets_knowledge_bases(self):
        fks = {fk.column.table.name for fk in KBSyncCursor.__table__.c["knowledge_base_id"].foreign_keys}
        assert "knowledge_bases" in fks

    def test_kb_sync_cursor_ds_fk_targets_data_sources(self):
        fks = {fk.column.table.name for fk in KBSyncCursor.__table__.c["data_source_id"].foreign_keys}
        assert "data_sources" in fks

    def test_kb_entity_kb_fk_targets_knowledge_bases(self):
        fks = {fk.column.table.name for fk in KBEntity.__table__.c["knowledge_base_id"].foreign_keys}
        assert "knowledge_bases" in fks

    def test_kb_relationship_kb_fk_targets_knowledge_bases(self):
        fks = {fk.column.table.name for fk in KBRelationship.__table__.c["knowledge_base_id"].foreign_keys}
        assert "knowledge_bases" in fks

    def test_kb_relationship_source_entity_fk_targets_kb_entities(self):
        fks = {fk.column.table.name for fk in KBRelationship.__table__.c["source_entity_id"].foreign_keys}
        assert "kb_entities" in fks

    def test_kb_relationship_source_doc_fk_targets_data_source_documents(self):
        fks = {fk.column.table.name for fk in KBRelationship.__table__.c["source_doc_id"].foreign_keys}
        assert "data_source_documents" in fks
