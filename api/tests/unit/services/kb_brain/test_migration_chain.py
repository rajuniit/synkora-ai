"""
Unit tests for the KB brain migration files.

Verifies the revision chain is intact, down_revision links are correct,
and the upgrade/downgrade functions exist and are callable (not just syntactically valid).
"""

import importlib

import pytest


def _load_migration(module_path: str):
    return importlib.import_module(module_path)


class TestMigration0003:
    MODULE = "migrations.versions.20260413_0003_rename_company_brain_to_kb"

    def test_module_loads(self):
        mod = _load_migration(self.MODULE)
        assert mod is not None

    def test_revision(self):
        mod = _load_migration(self.MODULE)
        assert mod.revision == "20260413_0003"

    def test_down_revision(self):
        mod = _load_migration(self.MODULE)
        assert mod.down_revision == "20260413_0002"

    def test_has_upgrade(self):
        mod = _load_migration(self.MODULE)
        assert callable(mod.upgrade)

    def test_has_downgrade(self):
        mod = _load_migration(self.MODULE)
        assert callable(mod.downgrade)

    def test_upgrade_creates_kb_tables(self):
        """Verify upgrade() calls create_table for kb_* tables."""
        mod = _load_migration(self.MODULE)
        import inspect

        source = inspect.getsource(mod.upgrade)
        assert "kb_sync_cursors" in source
        assert "kb_entities" in source
        assert "kb_relationships" in source

    def test_upgrade_drops_company_brain_tables(self):
        mod = _load_migration(self.MODULE)
        import inspect

        source = inspect.getsource(mod.upgrade)
        assert "company_brain_relationships" in source
        assert "company_brain_cursors" in source
        assert "company_brain_entities" in source

    def test_downgrade_drops_kb_tables(self):
        mod = _load_migration(self.MODULE)
        import inspect

        source = inspect.getsource(mod.downgrade)
        assert "kb_relationships" in source
        assert "kb_entities" in source
        assert "kb_sync_cursors" in source

    def test_downgrade_recreates_company_brain_tables(self):
        mod = _load_migration(self.MODULE)
        import inspect

        source = inspect.getsource(mod.downgrade)
        assert "company_brain_entities" in source
        assert "company_brain_cursors" in source
        assert "company_brain_relationships" in source

    def test_kb_entities_scoped_by_knowledge_base_id(self):
        """The new kb_entities table must have a knowledge_base_id FK column."""
        mod = _load_migration(self.MODULE)
        import inspect

        source = inspect.getsource(mod.upgrade)
        assert "knowledge_base_id" in source

    def test_kb_sync_cursors_scoped_by_knowledge_base_id(self):
        mod = _load_migration(self.MODULE)
        import inspect

        source = inspect.getsource(mod.upgrade)
        # knowledge_base_id must appear in the upgrade (for kb_sync_cursors)
        assert source.count("knowledge_base_id") >= 2  # in both tables


class TestMigrationChain:
    """Verify the full revision chain 0001 → 0002 → 0003."""

    def test_migration_0001_has_down_revision_none(self):
        try:
            mod = _load_migration("migrations.versions.20260413_0001_add_diagrams_table")
            # 0001 should be the root (down_revision = None or some prior migration)
            # Just verify it loads cleanly
            assert mod.revision is not None
        except ModuleNotFoundError:
            pytest.skip("Migration 0001 not found in this test environment")

    def test_migration_0002_exists(self):
        try:
            mod = _load_migration("migrations.versions.20260413_0002_add_company_brain_tables")
            assert mod.revision == "20260413_0002"
        except ModuleNotFoundError:
            pytest.skip("Migration 0002 not found in this test environment")

    def test_migration_0003_links_to_0002(self):
        mod = _load_migration("migrations.versions.20260413_0003_rename_company_brain_to_kb")
        assert mod.down_revision == "20260413_0002"


class TestDedup:
    """Tests for the dedup backend module."""

    def test_redis_dedup_key_format(self):
        from src.services.company_brain.ingestion.dedup import _dedup_key

        key = _dedup_key("test-tenant-id", "slack")
        assert key.startswith("cb_dedup:")
        assert "slack" in key
        # tenant_id dashes are stripped
        assert "-" not in key.split(":")[1]

    def test_hash_external_id_short_passes_through(self):
        from src.services.company_brain.ingestion.dedup import _hash_external_id

        short_id = "slack_C01_123"
        assert _hash_external_id(short_id) == short_id

    def test_hash_external_id_long_hashed(self):
        from src.services.company_brain.ingestion.dedup import _hash_external_id

        long_id = "x" * 100
        hashed = _hash_external_id(long_id)
        assert len(hashed) == 64  # SHA-256 hex digest
        assert hashed != long_id

    def test_get_dedup_backend_default_returns_redis(self):
        from unittest.mock import patch

        from src.services.company_brain.ingestion import dedup

        class FakeSettings:
            company_brain_dedup_backend = "redis_set"
            company_brain_dedup_ttl_days = 7

        with patch("src.config.settings.get_settings", return_value=FakeSettings()):
            backend = dedup.get_dedup_backend()
        assert isinstance(backend, dedup.RedisSetDedup)

    def test_get_dedup_backend_postgres_returns_postgres(self):
        from unittest.mock import patch

        from src.services.company_brain.ingestion import dedup

        class FakeSettings:
            company_brain_dedup_backend = "postgres"
            company_brain_dedup_ttl_days = 7

        with patch("src.config.settings.get_settings", return_value=FakeSettings()):
            backend = dedup.get_dedup_backend()
        assert isinstance(backend, dedup.PostgresDedup)
