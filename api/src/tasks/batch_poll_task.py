"""
Batch Poll Task

Celery task that polls pending LLM batch jobs every 30 minutes and records
completed results. Queries llm_token_usages rows where
optimization_flags->>'batch_status' = 'pending'.
"""

import logging

from src.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.poll_llm_batches", bind=True, max_retries=3)
def poll_llm_batches(self):
    """Poll pending LLM batch jobs and record completed results."""
    import asyncio

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_poll_batches_async())
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"poll_llm_batches error: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300) from exc


async def _poll_batches_async() -> None:
    """Async implementation: find pending batch rows, poll, update."""
    from sqlalchemy import select

    from src.core.database import create_celery_async_session
    from src.models.llm_token_usage import LLMTokenUsage
    from src.services.agents.llm_batch_client import get_batch_client

    factory = create_celery_async_session()
    async with factory() as db:
        # Find rows with pending batch jobs
        stmt = (
            select(LLMTokenUsage).where(LLMTokenUsage.optimization_flags["batch_status"].astext == "pending").limit(100)
        )

        result = await db.execute(stmt)
        pending_rows = result.scalars().all()

        if not pending_rows:
            logger.debug("poll_llm_batches: no pending batch jobs")
            return

        logger.info(f"poll_llm_batches: checking {len(pending_rows)} pending batch jobs")

        for row in pending_rows:
            try:
                flags = row.optimization_flags or {}
                batch_id = flags.get("batch_id")
                provider = row.provider
                if not batch_id:
                    continue

                # We don't store API keys in llm_token_usages — use a placeholder
                # client just to poll (API key fetched via agent config in real usage)
                # For polling we need the API key from the agent's config.
                # Look it up from the agent's primary LLM config.
                api_key = await _resolve_api_key(db, row)
                if not api_key:
                    logger.warning(f"poll_llm_batches: no API key for batch {batch_id}, skipping")
                    continue

                client = get_batch_client(provider, api_key, row.model_name)
                if not client:
                    continue

                status, results = await client.poll(batch_id)

                if status == "completed" and results:
                    # Update the row with actual token counts from the completed batch
                    total_input = sum(r.input_tokens for r in results)
                    total_output = sum(r.output_tokens for r in results)
                    new_flags = {**flags, "batch_status": "completed"}
                    row.input_tokens = total_input
                    row.output_tokens = total_output
                    row.optimization_flags = new_flags
                    logger.info(f"poll_llm_batches: batch {batch_id} completed ({total_input} in, {total_output} out)")
                elif status in ("failed", "expired", "cancelling", "cancelled"):
                    new_flags = {**flags, "batch_status": status}
                    row.optimization_flags = new_flags
                    logger.warning(f"poll_llm_batches: batch {batch_id} ended with status={status}")

            except Exception as e:
                logger.error(f"poll_llm_batches: error processing row {row.id}: {e}")
                continue

        await db.commit()


async def _resolve_api_key(db, row: "LLMTokenUsage") -> str | None:
    """Resolve the API key for a batch row by looking up the agent's LLM config."""
    from sqlalchemy import select

    from src.models.agent_llm_config import AgentLLMConfig
    from src.services.agents.security import decrypt_value

    if not row.agent_id:
        return None

    try:
        result = await db.execute(
            select(AgentLLMConfig)
            .where(
                AgentLLMConfig.agent_id == row.agent_id,
                AgentLLMConfig.enabled == True,  # noqa: E712
                AgentLLMConfig.is_default == True,  # noqa: E712
            )
            .limit(1)
        )
        cfg = result.scalar_one_or_none()
        if cfg and cfg.api_key:
            return decrypt_value(cfg.api_key)
    except Exception as e:
        logger.debug(f"_resolve_api_key error: {e}")
    return None
