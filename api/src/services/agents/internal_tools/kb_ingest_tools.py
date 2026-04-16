"""
Knowledge Base Ingest Tools for Synkora Agents.

Allows agents to persist URL content and manual text into a knowledge base
directly from a conversation. Reuses existing infrastructure:
  - web_tools.internal_web_fetch  (SSRF-protected URL fetching)
  - tasks.kb_tasks.crawl_and_process_kb  (Celery crawl task)
  - services.data_sources.document_processor.DocumentProcessor  (text ingestion)
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def internal_kb_crawl_url(
    url: str,
    knowledge_base_id: int,
    include_subpages: bool = True,
    max_pages: int = 50,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Crawl a URL (and optionally its subpages) and add the content to a knowledge base.

    The crawl runs as a background Celery task so this call returns immediately.
    Use include_subpages=True and a high max_pages to crawl an entire app or docs site.

    Args:
        url: Public HTTP/HTTPS starting URL to crawl.
        knowledge_base_id: Numeric ID of the target knowledge base.
        include_subpages: Follow same-domain links to crawl the whole site. Default True.
        max_pages: Maximum number of pages to crawl. Default 50, max 500.
        config: Optional tool config (injected by tool registry).

    Returns:
        dict with keys: success, message, url, knowledge_base_id, max_pages
    """
    from src.services.agents.internal_tools.web_tools import _is_url_safe

    if not url or not url.startswith(("http://", "https://")):
        return {"success": False, "error": "URL must start with http:// or https://"}

    is_safe, err = await _is_url_safe(url)
    if not is_safe:
        return {"success": False, "error": f"URL blocked for security reasons: {err}"}

    max_pages = min(max(1, max_pages), 500)  # clamp to [1, 500]

    try:
        from sqlalchemy import select

        from src.core.database import get_async_session_factory
        from src.models.data_source import DataSource, DataSourceStatus, DataSourceType
        from src.models.knowledge_base import KnowledgeBase
        from src.tasks.kb_tasks import crawl_and_process_kb

        async with get_async_session_factory()() as db:
            result = await db.execute(select(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id))
            kb = result.scalar_one_or_none()
            if not kb:
                return {"success": False, "error": f"Knowledge base {knowledge_base_id} not found"}

            # Get or create web data source for this KB
            result = await db.execute(
                select(DataSource).filter(
                    DataSource.knowledge_base_id == kb.id,
                    DataSource.type == DataSourceType.WEB,
                )
            )
            data_source = result.scalar_one_or_none()
            if not data_source:
                data_source = DataSource(
                    tenant_id=kb.tenant_id,
                    knowledge_base_id=kb.id,
                    name="Web Crawl",
                    type=DataSourceType.WEB,
                    status=DataSourceStatus.ACTIVE,
                )
                db.add(data_source)
                await db.commit()
                await db.refresh(data_source)

            kb_name = kb.name
            kb_tenant = str(kb.tenant_id)
            ds_id = data_source.id

        crawl_and_process_kb.delay(
            data_source_id=ds_id,
            tenant_id=kb_tenant,
            url=url,
            max_pages=max_pages,
            include_subpages=include_subpages,
        )

        scope = f"up to {max_pages} pages" if include_subpages else "single page"
        return {
            "success": True,
            "message": (
                f"Crawl queued ({scope}) starting at {url}. "
                f"Content will be added to knowledge base '{kb_name}' once processing completes."
            ),
            "url": url,
            "knowledge_base_id": knowledge_base_id,
            "max_pages": max_pages,
            "include_subpages": include_subpages,
        }

    except Exception as exc:
        logger.error(f"kb_crawl_url failed for {url}: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}


async def internal_kb_add_text(
    title: str,
    content: str,
    knowledge_base_id: int,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Add text content (e.g. a how-to guide or manual) to a knowledge base.

    The content is chunked, embedded, and indexed immediately in a background
    Celery task. Use this to create durable how-to guides, FAQs, or any
    reference material that agents should be able to retrieve later.

    Args:
        title: Human-readable title for the document.
        content: Full text content to store.
        knowledge_base_id: Numeric ID of the target knowledge base.
        config: Optional tool config (injected by tool registry).

    Returns:
        dict with keys: success, message, title, knowledge_base_id
    """
    if not title or not title.strip():
        return {"success": False, "error": "title must not be empty"}
    if not content or not content.strip():
        return {"success": False, "error": "content must not be empty"}

    try:
        from sqlalchemy import select

        from src.core.database import get_async_session_factory
        from src.models.data_source import DataSource, DataSourceStatus, DataSourceType
        from src.models.knowledge_base import KnowledgeBase
        from src.tasks.kb_tasks import process_kb_documents

        async with get_async_session_factory()() as db:
            result = await db.execute(select(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id))
            kb = result.scalar_one_or_none()
            if not kb:
                return {"success": False, "error": f"Knowledge base {knowledge_base_id} not found"}

            # Get or create manual data source for this KB
            result = await db.execute(
                select(DataSource).filter(
                    DataSource.knowledge_base_id == kb.id,
                    DataSource.type == DataSourceType.MANUAL,
                )
            )
            data_source = result.scalar_one_or_none()
            if not data_source:
                data_source = DataSource(
                    tenant_id=kb.tenant_id,
                    knowledge_base_id=kb.id,
                    name="Manual Entries",
                    type=DataSourceType.MANUAL,
                    status=DataSourceStatus.ACTIVE,
                )
                db.add(data_source)
                await db.commit()
                await db.refresh(data_source)

        documents = [
            {
                "id": title,
                "text": content,
                "metadata": {
                    "title": title,
                    "source_type": "manual",
                    "upload_source": "agent",
                },
            }
        ]
        process_kb_documents.delay(data_source.id, str(kb.tenant_id), documents)

        return {
            "success": True,
            "message": f"Content '{title}' queued and will be added to knowledge base {kb.name}.",
            "title": title,
            "knowledge_base_id": knowledge_base_id,
        }

    except Exception as exc:
        logger.error(f"kb_add_text failed (kb={knowledge_base_id}): {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}
