import json
import os
import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.integration_config import IntegrationConfig
from src.services.integrations.integration_config_service import IntegrationConfigService


class TestIntegrationConfigService:
    @pytest.fixture
    def mock_db_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db_session):
        # Mock get_encryption_key to return a valid key for Fernet
        from cryptography.fernet import Fernet

        valid_key = Fernet.generate_key()

        with patch("src.services.integrations.integration_config_service.get_encryption_key") as mock_key:
            mock_key.return_value = valid_key
            service = IntegrationConfigService(mock_db_session)
            return service

    def test_encrypt_decrypt_config(self, service):
        data = {"key": "value", "nested": {"a": 1}}
        encrypted = service._encrypt_config(data)
        assert encrypted != json.dumps(data)
        assert isinstance(encrypted, str)

        decrypted = service._decrypt_config(encrypted)
        assert decrypted == data

    async def test_create_config_success(self, service, mock_db_session):
        config_data = {"api_key": "secret"}
        tenant_id = uuid.uuid4()

        # Mock no existing platform config - return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.create_config(
            tenant_id=tenant_id, integration_type="email", provider="sendgrid", config_data=config_data, is_default=True
        )

        assert isinstance(result, IntegrationConfig)
        assert result.tenant_id == tenant_id
        assert result.integration_type == "email"
        assert result.provider == "sendgrid"
        assert result.is_default is True

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    async def test_create_config_platform_duplicate(self, service, mock_db_session):
        # Mock existing platform config
        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="A platform configuration already exists"):
            await service.create_config(tenant_id=None, integration_type="email", provider="smtp", config_data={})

    async def test_get_active_config_tenant_default(self, service, mock_db_session):
        tenant_id = uuid.uuid4()
        mock_config = MagicMock()

        # Mock the execute to return a config
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_active_config(tenant_id, "email", "smtp")
        assert result == mock_config

    async def test_get_active_config_fallback_platform(self, service, mock_db_session):
        tenant_id = uuid.uuid4()
        mock_platform_config = MagicMock()

        # Mock side_effect for execute to return None for tenant queries, then config for platform
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        mock_result_config = MagicMock()
        mock_result_config.scalar_one_or_none.return_value = mock_platform_config

        # tenant default -> None, tenant any -> None, platform default -> config
        mock_db_session.execute = AsyncMock(
            side_effect=[mock_result_none, mock_result_none, mock_result_config]
        )

        result = await service.get_active_config(tenant_id, "email", "smtp")
        assert result is not None
        assert result == mock_platform_config

    async def test_update_config(self, service, mock_db_session):
        config_id = uuid.uuid4()
        mock_config = IntegrationConfig(id=config_id)

        # Mock get_config to return the config
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        new_data = {"new": "value"}
        result = await service.update_config(config_id, config_data=new_data, is_active=False)

        assert result == mock_config
        assert result.is_active is False
        # Verify data encrypted
        assert service._decrypt_config(result.config_data) == new_data
        mock_db_session.commit.assert_called_once()

    async def test_delete_config(self, service, mock_db_session):
        config_id = uuid.uuid4()
        mock_config = IntegrationConfig(id=config_id)

        # Mock get_config to return the config
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        result = await service.delete_config(config_id)

        assert result is True
        mock_db_session.delete.assert_called_with(mock_config)
        mock_db_session.commit.assert_called_once()

    async def test_get_app_base_url(self, service):
        # Mock get_active_config_data
        with patch.object(service, "get_active_config_data", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"app_base_url": "https://custom.app/"}

            url = await service.get_app_base_url(uuid.uuid4())
            assert url == "https://custom.app"

            mock_get.return_value = None
            with patch.dict(os.environ, {"APP_BASE_URL": "https://env.app"}):
                url = await service.get_app_base_url()
                assert url == "https://env.app"
