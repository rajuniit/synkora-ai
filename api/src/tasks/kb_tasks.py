"""
Celery tasks for knowledge base document processing.

Handles chunking, embedding and storage as background jobs so HTTP
requests return immediately.
"""

import asyncio
import logging
from typing import Any

from src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.process_kb_documents", bind=True, max_retries=2, default_retry_delay=30)
def process_kb_documents(self, data_source_id: int, tenant_id: str, documents: list[dict[str, Any]]) -> dict:
    """
    Chunk and embed documents for a knowledge base data source.

    Args:
        data_source_id: ID of the DataSource record
        tenant_id: Tenant UUID string
        documents: List of {id, text, metadata} dicts already extracted from files
    """
    try:
        asyncio.run(_process_kb_documents(data_source_id, tenant_id, documents))
        return {"status": "completed", "documents": len(documents)}
    except Exception as exc:
        logger.error(f"process_kb_documents failed for data_source={data_source_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(name="tasks.crawl_and_process_kb", bind=True, max_retries=1, default_retry_delay=60)
def crawl_and_process_kb(
    self,
    data_source_id: int,
    tenant_id: str,
    url: str,
    max_pages: int,
    include_subpages: bool,
) -> dict:
    """
    Crawl a website and embed its content into a knowledge base data source.

    Args:
        data_source_id: ID of the DataSource record
        tenant_id: Tenant UUID string
        url: Starting URL to crawl
        max_pages: Maximum number of pages to crawl
        include_subpages: Whether to follow same-domain links
    """
    try:
        asyncio.run(_crawl_and_process_kb(data_source_id, tenant_id, url, max_pages, include_subpages))
        return {"status": "completed"}
    except Exception as exc:
        logger.error(f"crawl_and_process_kb failed for data_source={data_source_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(name="tasks.analyze_app_store_reviews", bind=True, max_retries=1, default_retry_delay=60)
def analyze_app_store_reviews(
    self,
    source_id: str,
    tenant_id: str,
    llm_provider: str,
    llm_model: str,
    llm_api_key: str,
    limit: int,
    only_unanalyzed: bool,
) -> dict:
    """
    Analyze app store reviews using LLM in the background.

    Args:
        source_id: AppStoreSource UUID string
        tenant_id: Tenant UUID string
        llm_provider: LLM provider name
        llm_model: LLM model name
        llm_api_key: API key for the LLM provider
        limit: Max reviews to analyze
        only_unanalyzed: Whether to skip already-analyzed reviews
    """
    try:
        asyncio.run(
            _analyze_app_store_reviews(
                source_id, tenant_id, llm_provider, llm_model, llm_api_key, limit, only_unanalyzed
            )
        )
        return {"status": "completed"}
    except Exception as exc:
        logger.error(f"analyze_app_store_reviews failed for source={source_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Async implementations
# ---------------------------------------------------------------------------


async def _process_kb_documents(data_source_id: int, tenant_id: str, documents: list[dict[str, Any]]) -> None:
    from sqlalchemy import select

    from src.core.database import async_session_factory
    from src.models.data_source import DataSource
    from src.services.data_sources.document_processor import DocumentProcessor

    async with async_session_factory() as db:
        result = await db.execute(select(DataSource).filter(DataSource.id == data_source_id))
        data_source = result.scalar_one_or_none()
        if not data_source:
            logger.error(f"DataSource {data_source_id} not found — cannot process documents")
            return

        processor = DocumentProcessor(db)
        result = await processor.process_documents(data_source=data_source, documents=documents)
        logger.info(f"KB document processing done for data_source={data_source_id}: {result}")


async def _crawl_and_process_kb(
    data_source_id: int, tenant_id: str, url: str, max_pages: int, include_subpages: bool
) -> None:
    import asyncio as _asyncio
    from urllib.parse import urljoin, urlparse

    import requests
    from bs4 import BeautifulSoup
    from sqlalchemy import select

    from src.core.database import async_session_factory
    from src.models.data_source import DataSource
    from src.services.data_sources.document_processor import DocumentProcessor
    from src.services.security.url_validator import validate_url

    parsed_url = urlparse(url)
    documents = []
    visited_urls: set[str] = set()
    urls_to_crawl = [url]

    while urls_to_crawl and len(documents) < max_pages:
        current_url = urls_to_crawl.pop(0)
        if current_url in visited_urls:
            continue
        visited_urls.add(current_url)

        try:
            is_url_valid, url_error = validate_url(
                current_url, allowed_schemes=["http", "https"], block_private_ips=True, resolve_dns=True
            )
            if not is_url_valid:
                logger.warning(f"SSRF blocked during crawl: {current_url} - {url_error}")
                continue

            headers = {"User-Agent": "Mozilla/5.0 (compatible; AIBot/1.0)"}
            loop = _asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda u=current_url: requests.get(u, headers=headers, timeout=30)
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            title = soup.title.string if soup.title else current_url

            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            text_content = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text_content.splitlines() if line.strip()]
            text_content = "\n".join(lines)

            if text_content:
                documents.append(
                    {
                        "id": current_url,
                        "text": text_content,
                        "metadata": {
                            "title": title,
                            "url": current_url,
                            "source_type": "web",
                            "upload_source": "crawl",
                        },
                    }
                )
                logger.info(f"Crawled: {current_url}")

            if include_subpages and len(documents) < max_pages:
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    full_url = urljoin(current_url, href)
                    parsed_full = urlparse(full_url)
                    if (
                        parsed_full.netloc == parsed_url.netloc
                        and full_url not in visited_urls
                        and not href.startswith(("#", "mailto:", "javascript:"))
                    ):
                        urls_to_crawl.append(full_url)

        except Exception as e:
            logger.warning(f"Failed to crawl {current_url}: {e}")
            continue

    if not documents:
        logger.warning(f"No content extracted from {url} for data_source={data_source_id}")
        return

    async with async_session_factory() as db:
        result = await db.execute(select(DataSource).filter(DataSource.id == data_source_id))
        data_source = result.scalar_one_or_none()
        if not data_source:
            logger.error(f"DataSource {data_source_id} not found after crawl")
            return

        processor = DocumentProcessor(db)
        result = await processor.process_documents(data_source=data_source, documents=documents)
        logger.info(f"Crawl+process done for data_source={data_source_id}, pages={len(documents)}: {result}")


async def _analyze_app_store_reviews(
    source_id: str,
    tenant_id: str,
    llm_provider: str,
    llm_model: str,
    llm_api_key: str,
    limit: int,
    only_unanalyzed: bool,
) -> None:
    import uuid

    from src.core.database import async_session_factory
    from src.services.agents.config import ModelConfig
    from src.services.app_store.review_analysis_service import ReviewAnalysisService

    async with async_session_factory() as db:
        analysis_service = ReviewAnalysisService(db)
        llm_config = ModelConfig(provider=llm_provider, model_name=llm_model, api_key=llm_api_key)
        analysis_service.initialize_llm_client(llm_config)
        result = await analysis_service.analyze_batch(
            app_store_source_id=uuid.UUID(source_id),
            limit=limit,
            only_unanalyzed=only_unanalyzed,
        )
        logger.info(f"App store review analysis done for source={source_id}: {result}")
