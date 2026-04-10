"""
Wiki Article and Compilation Job models for Knowledge Autopilot.

WikiArticle stores auto-generated wiki pages from knowledge base documents.
WikiCompilationJob tracks compilation runs.
"""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.models.base import BaseModel, TenantMixin


class WikiArticle(BaseModel, TenantMixin):
    """An auto-generated wiki article from knowledge base documents."""

    __tablename__ = "wiki_articles"

    knowledge_base_id = Column(
        Integer, nullable=False, index=True,
        comment="Knowledge base this article belongs to",
    )
    title = Column(String(500), nullable=False, comment="Article title")
    slug = Column(String(500), nullable=False, index=True, comment="URL-friendly slug")
    content = Column(Text, nullable=False, default="", comment="Markdown content")
    category = Column(
        String(100), nullable=False, default="general",
        comment="Category: projects, people, decisions, processes, architecture, general",
    )
    summary = Column(Text, nullable=True, comment="Brief summary for index pages")
    source_documents = Column(
        JSON, nullable=False, default=list,
        comment="Source doc refs [{doc_id, doc_title, relevance}]",
    )
    backlinks = Column(
        JSON, nullable=False, default=list,
        comment="Article IDs that link to this article",
    )
    forward_links = Column(
        JSON, nullable=False, default=list,
        comment="Article IDs this article links to",
    )
    auto_generated = Column(
        Boolean, nullable=False, default=True,
        comment="Whether this was auto-generated (vs manually edited)",
    )
    last_compiled_at = Column(
        DateTime(timezone=True), nullable=True,
        comment="When this article was last compiled/updated",
    )
    staleness_score = Column(
        Float, nullable=False, default=0.0,
        comment="0 = fresh, 1 = stale (based on newer source data)",
    )
    status = Column(
        String(50), nullable=False, default="published",
        comment="draft, published, stale, archived",
    )


class WikiCompilationJob(BaseModel, TenantMixin):
    """Tracks a wiki compilation run."""

    __tablename__ = "wiki_compilation_jobs"

    knowledge_base_id = Column(
        Integer, nullable=False, index=True,
        comment="Knowledge base being compiled",
    )
    status = Column(
        String(50), nullable=False, default="running",
        comment="running, completed, failed",
    )
    started_at = Column(DateTime(timezone=True), nullable=True, comment="When compilation started")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="When compilation finished")
    articles_created = Column(Integer, nullable=False, default=0, comment="Number of new articles")
    articles_updated = Column(Integer, nullable=False, default=0, comment="Number of updated articles")
    errors = Column(JSON, nullable=False, default=list, comment="Any errors during compilation")
    compilation_metadata = Column(
        JSON, nullable=True, default=dict,
        comment="Additional stats: tokens_used, documents_processed, etc.",
    )
