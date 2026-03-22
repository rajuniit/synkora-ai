import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.agent_context_file import AgentContextFile
from src.services.agents.context_file_processor import AgentContextFileProcessor


class TestAgentContextFileProcessor:
    @pytest.fixture
    def mock_db(self):
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def processor(self, mock_db):
        with patch("src.services.agents.context_file_processor.S3StorageService") as MockS3:
            processor = AgentContextFileProcessor(mock_db)
            processor.s3_storage = MockS3.return_value
            return processor

    @pytest.fixture
    def mock_agent(self):
        agent = MagicMock(spec=Agent)
        agent.id = uuid.uuid4()
        agent.tenant_id = uuid.uuid4()
        agent.agent_name = "Test Agent"
        agent.context_files = []
        return agent

    def test_validate_file_success(self, processor):
        valid, error = processor.validate_file("test.txt", 100, "text/plain")
        assert valid is True
        assert error is None

    def test_validate_file_invalid_type(self, processor):
        valid, error = processor.validate_file("test.exe", 100, "application/x-msdownload")
        assert valid is False
        assert "Unsupported file type" in error

    def test_validate_file_too_large(self, processor):
        large_size = 60 * 1024 * 1024  # 60MB
        valid, error = processor.validate_file("test.pdf", large_size, "application/pdf")
        assert valid is False
        assert "File size exceeds maximum" in error

    def test_validate_agent_limits_success(self, processor, mock_agent):
        valid, error = processor.validate_agent_limits(mock_agent, 100)
        assert valid is True
        assert error is None

    def test_validate_agent_limits_too_many_files(self, processor, mock_agent):
        mock_agent.context_files = [MagicMock()] * 100
        valid, error = processor.validate_agent_limits(mock_agent, 100)
        assert valid is False
        assert "Maximum of 100 files" in error

    def test_validate_agent_limits_total_size_exceeded(self, processor, mock_agent):
        mock_file = MagicMock()
        mock_file.file_size = 150 * 1024 * 1024
        mock_agent.context_files = [mock_file]

        new_size = 60 * 1024 * 1024
        valid, error = processor.validate_agent_limits(mock_agent, new_size)
        assert valid is False
        assert "Total file size would exceed" in error

    @pytest.mark.asyncio
    async def test_process_file_success(self, processor, mock_agent):
        file_content = b"Hello World"
        file_obj = io.BytesIO(file_content)
        processor.s3_storage.upload_file_content = AsyncMock(return_value="s3://url")
        processor.s3_storage.bucket_name = "test-bucket"

        result = await processor.process_file(mock_agent, file_obj, "test.txt", "text/plain")

        assert isinstance(result, AgentContextFile)
        assert result.filename == "test.txt"
        assert result.extracted_text == "Hello World"
        assert result.extraction_status == "COMPLETED"
        processor.db.add.assert_called_once()
        processor.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_extraction_failure(self, processor, mock_agent):
        file_content = b"Bad Content"
        file_obj = io.BytesIO(file_content)
        processor.s3_storage.upload_file_content = AsyncMock(return_value="s3://url")
        processor.s3_storage.bucket_name = "test-bucket"

        # Mock extraction failure
        with patch.object(processor, "_extract_text", side_effect=Exception("Extraction Failed")):
            result = await processor.process_file(mock_agent, file_obj, "test.txt", "text/plain")

            assert result.extraction_status == "FAILED"
            assert "Extraction Failed" in result.extraction_error

    def test_extract_text_pdf(self, processor):
        # Mock PyPDF2
        with patch("src.services.agents.context_file_processor.PyPDF2.PdfReader") as MockReader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "PDF Content"
            MockReader.return_value.pages = [mock_page]

            text = processor._extract_text_from_pdf(b"pdf data")
            assert "PDF Content" in text

    def test_extract_text_docx(self, processor):
        # Mock docx
        with patch("src.services.agents.context_file_processor.docx.Document") as MockDoc:
            mock_para = MagicMock()
            mock_para.text = "Docx Content"
            MockDoc.return_value.paragraphs = [mock_para]
            MockDoc.return_value.tables = []

            text = processor._extract_text_from_docx(b"docx data")
            assert "Docx Content" in text

    def test_extract_text_csv(self, processor):
        csv_content = b"col1,col2\nval1,val2"
        text = processor._extract_text_from_csv(csv_content)
        assert "col1 | col2" in text
        assert "val1 | val2" in text

    @pytest.mark.asyncio
    async def test_delete_file(self, processor):
        mock_file = MagicMock(spec=AgentContextFile)
        mock_file.s3_key = "key"
        mock_file.filename = "file.txt"

        await processor.delete_file(mock_file)

        processor.s3_storage.delete_file.assert_called_with("key")
        processor.db.delete.assert_called_with(mock_file)
        processor.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_download_url(self, processor):
        mock_file = MagicMock(spec=AgentContextFile)
        mock_file.s3_key = "key"
        processor.s3_storage.generate_presigned_url = AsyncMock(return_value="url")

        url = await processor.get_download_url(mock_file)
        assert url == "url"

    def test_get_context_files_text(self, processor, mock_agent):
        file1 = MagicMock()
        file1.is_extraction_complete = True
        file1.extracted_text = "Content 1"
        file1.filename = "file1.txt"

        file2 = MagicMock()
        file2.is_extraction_complete = False  # Should be skipped

        mock_agent.context_files = [file1, file2]

        text = processor.get_context_files_text(mock_agent)
        assert "Content 1" in text
        assert "file1.txt" in text
