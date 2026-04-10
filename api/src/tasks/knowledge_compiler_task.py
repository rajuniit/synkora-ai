"""
Celery tasks for scheduled Knowledge Autopilot compilation.

Periodically compiles knowledge bases that have autopilot enabled,
generating and updating wiki articles from source documents.
"""

import asyncio
import logging

from src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.compile_knowledge_wikis", bind=True, max_retries=1)
def compile_knowledge_wikis(self):
    """
    Periodic task: find all knowledge bases with wiki articles and recompile.

    Runs daily to detect new/updated documents and refresh wiki articles.
    """
    asyncio.run(_compile_all_wikis())


async def _compile_all_wikis():
    from sqlalchemy import select, func

    from src.core.database import async_session_factory
    from src.models.wiki_article import WikiArticle
    from src.services.knowledge_autopilot.compiler import KnowledgeCompiler

    async with async_session_factory() as db:
        # Find all knowledge bases that have at least one wiki article (autopilot active)
        result = await db.execute(
            select(WikiArticle.knowledge_base_id, WikiArticle.tenant_id)
            .group_by(WikiArticle.knowledge_base_id, WikiArticle.tenant_id)
        )
        kb_tenants = result.all()

        if not kb_tenants:
            logger.info("No knowledge bases with wiki articles found, skipping compilation")
            return

        compiler = KnowledgeCompiler(db)
        compiled = 0
        failed = 0

        for kb_id, tenant_id in kb_tenants:
            try:
                result = await compiler.compile(
                    knowledge_base_id=str(kb_id),
                    tenant_id=str(tenant_id),
                )
                if result.get("status") == "completed":
                    compiled += 1
                else:
                    failed += 1
                logger.info(f"Compiled KB {kb_id}: {result.get('status')}")
            except Exception as e:
                failed += 1
                logger.error(f"Failed to compile KB {kb_id}: {e}")

        logger.info(f"Knowledge wiki compilation complete: {compiled} succeeded, {failed} failed")
