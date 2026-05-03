"""
Knowledge Autopilot Controller — Wiki generation and browsing endpoints.

Provides endpoints to enable autopilot on a knowledge base, trigger compilations,
browse wiki articles, and query the wiki graph.
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_account, get_current_tenant_id
from src.models.knowledge_base import KnowledgeBase
from src.models.tenant import Account
from src.models.wiki_article import WikiArticle, WikiCompilationJob
from src.tasks.knowledge_compiler_task import compile_single_knowledge_wiki


class CompileRequest(BaseModel):
    llm_config_id: str | None = None


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/knowledge-bases/{kb_id}/autopilot/llm-configs")
async def list_llm_configs_for_compilation(
    kb_id: int,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """List all enabled LLM configs available for wiki compilation (across all tenant agents)."""
    from sqlalchemy import join

    from src.models.agent import Agent
    from src.models.agent_llm_config import AgentLLMConfig

    result = await db.execute(
        select(AgentLLMConfig, Agent.agent_name)
        .join(Agent, AgentLLMConfig.agent_id == Agent.id)
        .filter(
            Agent.tenant_id == tenant_id,
            AgentLLMConfig.enabled.is_(True),
        )
        .order_by(Agent.agent_name, AgentLLMConfig.name)
    )
    rows = result.all()

    return {
        "configs": [
            {
                "id": str(row.AgentLLMConfig.id),
                "name": row.AgentLLMConfig.name,
                "provider": row.AgentLLMConfig.provider,
                "model_name": row.AgentLLMConfig.model_name,
                "agent_name": row.agent_name,
            }
            for row in rows
        ]
    }


@router.post("/knowledge-bases/{kb_id}/autopilot/compile")
async def trigger_compilation(
    kb_id: int,
    body: CompileRequest = CompileRequest(),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """Trigger a manual wiki compilation for a knowledge base (runs as background Celery task)."""
    result = await db.execute(
        select(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.tenant_id == tenant_id,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    compile_single_knowledge_wiki.delay(kb_id, str(tenant_id), body.llm_config_id)

    return {"status": "queued", "message": "Compilation started in the background. Refresh the page in a moment."}


@router.get("/knowledge-bases/{kb_id}/wiki")
async def list_wiki_articles(
    kb_id: int,
    category: str | None = Query(None),
    status: str = Query("published"),
    limit: int = Query(100, ge=1, le=500),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """Browse wiki articles for a knowledge base."""
    query = select(WikiArticle).filter(
        WikiArticle.knowledge_base_id == kb_id,
        WikiArticle.tenant_id == tenant_id,
        WikiArticle.status == status,
    )

    if category:
        query = query.filter(WikiArticle.category == category)

    query = query.order_by(WikiArticle.title).limit(limit)
    result = await db.execute(query)
    articles = result.scalars().all()

    # Group by category
    categories: dict[str, list] = {}
    for article in articles:
        cat = article.category or "general"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(_article_to_dict(article, include_content=False))

    return {
        "articles": [_article_to_dict(a, include_content=False) for a in articles],
        "categories": categories,
        "total": len(articles),
    }


@router.get("/knowledge-bases/{kb_id}/wiki/article/{slug}")
async def get_wiki_article(
    kb_id: int,
    slug: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a single wiki article by slug."""
    result = await db.execute(
        select(WikiArticle).filter(
            WikiArticle.knowledge_base_id == kb_id,
            WikiArticle.tenant_id == tenant_id,
            WikiArticle.slug == slug,
        )
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Fetch linked articles for display
    linked_ids = list(set((article.forward_links or []) + (article.backlinks or [])))
    linked_articles = []
    if linked_ids:
        linked_result = await db.execute(select(WikiArticle).filter(WikiArticle.id.in_(linked_ids)))
        linked_articles = [
            {"id": str(a.id), "title": a.title, "slug": a.slug, "category": a.category}
            for a in linked_result.scalars().all()
        ]

    data = _article_to_dict(article, include_content=True)
    data["linked_articles"] = linked_articles
    return data


@router.get("/knowledge-bases/{kb_id}/wiki/graph")
async def get_wiki_graph(
    kb_id: int,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """Get article relationship graph data for visualization."""
    result = await db.execute(
        select(WikiArticle).filter(
            WikiArticle.knowledge_base_id == kb_id,
            WikiArticle.tenant_id == tenant_id,
            WikiArticle.status == "published",
        )
    )
    articles = result.scalars().all()

    nodes = []
    links = []

    for article in articles:
        nodes.append(
            {
                "id": str(article.id),
                "title": article.title,
                "slug": article.slug,
                "category": article.category,
                "staleness": article.staleness_score,
            }
        )

        for target_id in article.forward_links or []:
            links.append(
                {
                    "source": str(article.id),
                    "target": target_id,
                }
            )

    return {"nodes": nodes, "links": links}


@router.post("/knowledge-bases/{kb_id}/wiki/search")
async def search_wiki(
    kb_id: int,
    query: dict,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """Search wiki articles by text."""
    search_term = query.get("q", "").strip()
    if not search_term:
        raise HTTPException(status_code=400, detail="Search query required")

    # Simple ILIKE search on title and content
    pattern = f"%{search_term}%"
    result = await db.execute(
        select(WikiArticle)
        .filter(
            WikiArticle.knowledge_base_id == kb_id,
            WikiArticle.tenant_id == tenant_id,
            WikiArticle.status == "published",
            (WikiArticle.title.ilike(pattern) | WikiArticle.content.ilike(pattern)),
        )
        .limit(20)
    )
    articles = result.scalars().all()

    return {
        "results": [_article_to_dict(a, include_content=False) for a in articles],
        "total": len(articles),
    }


@router.get("/knowledge-bases/{kb_id}/autopilot/status")
async def get_autopilot_status(
    kb_id: int,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_account: Account = Depends(get_current_account),
    db: AsyncSession = Depends(get_async_db),
):
    """Get autopilot status including last compilation and article stats."""
    # Latest compilation job
    job_result = await db.execute(
        select(WikiCompilationJob)
        .filter(
            WikiCompilationJob.knowledge_base_id == kb_id,
            WikiCompilationJob.tenant_id == tenant_id,
        )
        .order_by(WikiCompilationJob.created_at.desc())
        .limit(1)
    )
    last_job = job_result.scalar_one_or_none()

    # Article stats
    stats_result = await db.execute(
        select(
            func.count(WikiArticle.id),
            func.avg(WikiArticle.staleness_score),
        ).filter(
            WikiArticle.knowledge_base_id == kb_id,
            WikiArticle.tenant_id == tenant_id,
            WikiArticle.status == "published",
        )
    )
    row = stats_result.one()
    total_articles = row[0] or 0
    avg_staleness = float(row[1] or 0)

    # Category counts
    cat_result = await db.execute(
        select(WikiArticle.category, func.count(WikiArticle.id))
        .filter(
            WikiArticle.knowledge_base_id == kb_id,
            WikiArticle.tenant_id == tenant_id,
            WikiArticle.status == "published",
        )
        .group_by(WikiArticle.category)
    )
    category_counts = dict(cat_result.all())

    return {
        "total_articles": total_articles,
        "avg_staleness": round(avg_staleness, 2),
        "category_counts": category_counts,
        "last_compilation": {
            "id": str(last_job.id) if last_job else None,
            "status": last_job.status if last_job else None,
            "started_at": last_job.started_at.isoformat() if last_job and last_job.started_at else None,
            "completed_at": last_job.completed_at.isoformat() if last_job and last_job.completed_at else None,
            "articles_created": last_job.articles_created if last_job else 0,
            "articles_updated": last_job.articles_updated if last_job else 0,
        }
        if last_job
        else None,
    }


def _article_to_dict(article: WikiArticle, include_content: bool = True) -> dict[str, Any]:
    """Convert WikiArticle to API response dict."""
    data = {
        "id": str(article.id),
        "title": article.title,
        "slug": article.slug,
        "category": article.category,
        "summary": article.summary,
        "staleness_score": article.staleness_score,
        "status": article.status,
        "auto_generated": article.auto_generated,
        "source_documents": article.source_documents or [],
        "backlinks": article.backlinks or [],
        "forward_links": article.forward_links or [],
        "last_compiled_at": article.last_compiled_at.isoformat() if article.last_compiled_at else None,
        "created_at": article.created_at.isoformat() if article.created_at else None,
    }
    if include_content:
        data["content"] = article.content
    return data
