"""Test Run API endpoints."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_db
from src.middleware.auth_middleware import get_current_tenant_id
from src.models.load_test import LoadTest, LoadTestStatus
from src.models.test_result import MetricType, TestResult
from src.models.test_run import TestRun, TestRunStatus
from src.schemas.load_testing import (
    ExportRequest,
    ExportResponse,
    MetricsSummary,
    StartTestRunRequest,
    TestResultResponse,
    TestResultsResponse,
    TestRunDetailResponse,
    TestRunListResponse,
    TestRunResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test-runs", tags=["test-runs"])


# ============================================================================
# Test Run Endpoints
# ============================================================================


@router.post("/{load_test_id}/run", response_model=TestRunResponse, status_code=201)
async def start_test_run(
    load_test_id: UUID,
    request: StartTestRunRequest | None = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Start a new test run for a load test."""
    try:
        # Get load test
        load_test = await _get_load_test(db, load_test_id, tenant_id)

        # Check if test is already running
        result = await db.execute(
            select(TestRun).filter(
                TestRun.load_test_id == load_test_id,
                TestRun.status.in_([TestRunStatus.PENDING, TestRunStatus.RUNNING, TestRunStatus.INITIALIZING]),
            )
        )
        existing_run = result.scalar_one_or_none()
        if existing_run:
            raise HTTPException(
                status_code=400,
                detail="A test run is already in progress for this load test",
            )

        # Update load test status
        load_test.status = LoadTestStatus.RUNNING

        # Create test run
        test_run = TestRun(
            tenant_id=tenant_id,
            load_test_id=load_test_id,
            status=TestRunStatus.PENDING,
            k6_options=request.k6_options if request else None,
        )

        db.add(test_run)
        await db.commit()
        await db.refresh(test_run)

        # Trigger async execution via Celery
        from src.tasks.load_testing_tasks import execute_load_test

        execute_load_test.delay(str(test_run.id))

        logger.info(f"Started test run: {test_run.id} for load test: {load_test_id}")

        return _test_run_to_response(test_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting test run: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=TestRunListResponse)
async def list_test_runs(
    load_test_id: UUID | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List test runs, optionally filtered by load test or status."""
    try:
        query = select(TestRun).filter(TestRun.tenant_id == tenant_id)

        if load_test_id:
            query = query.filter(TestRun.load_test_id == load_test_id)

        if status:
            try:
                status_enum = TestRunStatus(status)
                query = query.filter(TestRun.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination and ordering
        query = query.order_by(TestRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        test_runs = result.scalars().all()

        return TestRunListResponse(
            items=[_test_run_to_response(tr) for tr in test_runs],
            total=total,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing test runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{test_run_id}", response_model=TestRunDetailResponse)
async def get_test_run(
    test_run_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Get detailed information about a test run."""
    try:
        test_run = await _get_test_run(db, test_run_id, tenant_id)
        return _test_run_to_detail_response(test_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{test_run_id}/cancel", response_model=TestRunResponse)
async def cancel_test_run(
    test_run_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Cancel a running test."""
    try:
        test_run = await _get_test_run(db, test_run_id, tenant_id)

        if not test_run.is_active:
            raise HTTPException(status_code=400, detail="Test run is not active")

        # Update status to stopping
        test_run.status = TestRunStatus.STOPPING

        # Trigger cancellation via Celery
        from src.tasks.load_testing_tasks import cancel_load_test

        cancel_load_test.delay(str(test_run_id))

        await db.commit()
        await db.refresh(test_run)

        logger.info(f"Cancelling test run: {test_run_id}")

        return _test_run_to_response(test_run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling test run: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{test_run_id}/results", response_model=TestResultsResponse)
async def get_test_results(
    test_run_id: UUID,
    metric_types: list[str] | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Get test results and metrics for a test run."""
    try:
        test_run = await _get_test_run(db, test_run_id, tenant_id)

        # Build query
        query = select(TestResult).filter(TestResult.test_run_id == test_run_id)

        if metric_types:
            valid_types = []
            for mt in metric_types:
                try:
                    valid_types.append(MetricType(mt))
                except ValueError:
                    pass  # Skip invalid types
            if valid_types:
                query = query.filter(TestResult.metric_type.in_(valid_types))

        if start_time:
            query = query.filter(TestResult.timestamp >= start_time)
        if end_time:
            query = query.filter(TestResult.timestamp <= end_time)

        query = query.order_by(TestResult.timestamp).limit(limit)

        result = await db.execute(query)
        results = result.scalars().all()

        # Build summary from test run's summary_metrics
        summary = MetricsSummary()
        if test_run.summary_metrics:
            summary = MetricsSummary(**test_run.summary_metrics)

        return TestResultsResponse(
            test_run_id=test_run_id,
            summary=summary,
            time_series=[_result_to_response(r) for r in results],
            total_points=len(results),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{test_run_id}/stream")
async def stream_test_results(
    test_run_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Stream real-time test results via SSE."""
    try:
        # Verify ownership
        await _get_test_run(db, test_run_id, tenant_id)

        async def event_generator():
            import asyncio
            import json

            from src.config.redis import get_redis_async

            redis = get_redis_async()
            channel_name = f"test_run:{test_run_id}:results"
            pubsub = redis.pubsub()
            await pubsub.subscribe(channel_name)

            try:
                while True:
                    # Non-blocking async get — does not stall the event loop
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                    if message and message["type"] == "message":
                        data = json.loads(message["data"])
                        yield f"data: {json.dumps(data)}\n\n"
                    else:
                        # Send heartbeat
                        yield ": heartbeat\n\n"
                        await asyncio.sleep(1)

                    # Check if test run is still active
                    result = await db.execute(select(TestRun.status).filter(TestRun.id == test_run_id))
                    status = result.scalar_one_or_none()
                    if status and status not in [
                        TestRunStatus.PENDING,
                        TestRunStatus.INITIALIZING,
                        TestRunStatus.RUNNING,
                    ]:
                        # Send completion event
                        yield f"data: {json.dumps({'event': 'complete', 'status': status.value})}\n\n"
                        break

            finally:
                await pubsub.unsubscribe(channel_name)
                await pubsub.aclose()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming test results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{test_run_id}/export", response_model=ExportResponse)
async def export_test_results(
    test_run_id: UUID,
    request: ExportRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Export test results to JSON, CSV, or PDF."""
    try:
        test_run = await _get_test_run(db, test_run_id, tenant_id)

        if test_run.is_active:
            raise HTTPException(status_code=400, detail="Cannot export results while test is running")

        # Generate export via Celery task
        from src.tasks.load_testing_tasks import generate_test_report

        task_result = generate_test_report.delay(
            str(test_run_id),
            request.format,
            request.include_time_series,
            request.include_k6_script,
        )

        # Wait for result (with timeout)
        result = task_result.get(timeout=60)

        return ExportResponse(
            download_url=result["download_url"],
            expires_at=datetime.fromisoformat(result["expires_at"]),
            format=request.format,
            file_size=result["file_size"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting test results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions
# ============================================================================


async def _get_load_test(db: AsyncSession, load_test_id: UUID, tenant_id: UUID) -> LoadTest:
    """Get a load test by ID with tenant verification."""
    result = await db.execute(select(LoadTest).filter(LoadTest.id == load_test_id, LoadTest.tenant_id == tenant_id))
    load_test = result.scalar_one_or_none()

    if not load_test:
        raise HTTPException(status_code=404, detail="Load test not found")

    return load_test


async def _get_test_run(db: AsyncSession, test_run_id: UUID, tenant_id: UUID) -> TestRun:
    """Get a test run by ID with tenant verification."""
    result = await db.execute(select(TestRun).filter(TestRun.id == test_run_id, TestRun.tenant_id == tenant_id))
    test_run = result.scalar_one_or_none()

    if not test_run:
        raise HTTPException(status_code=404, detail="Test run not found")

    return test_run


def _test_run_to_response(test_run: TestRun) -> TestRunResponse:
    """Convert TestRun model to response schema."""
    return TestRunResponse(
        id=test_run.id,
        tenant_id=test_run.tenant_id,
        load_test_id=test_run.load_test_id,
        status=test_run.status.value,
        started_at=test_run.started_at,
        completed_at=test_run.completed_at,
        summary_metrics=test_run.summary_metrics,
        error_message=test_run.error_message,
        peak_vus=test_run.peak_vus,
        total_requests=test_run.total_requests,
        duration_seconds=test_run.duration_seconds,
        is_active=test_run.is_active,
        created_at=test_run.created_at,
        updated_at=test_run.updated_at,
    )


def _test_run_to_detail_response(test_run: TestRun) -> TestRunDetailResponse:
    """Convert TestRun model to detailed response schema."""
    return TestRunDetailResponse(
        id=test_run.id,
        tenant_id=test_run.tenant_id,
        load_test_id=test_run.load_test_id,
        status=test_run.status.value,
        started_at=test_run.started_at,
        completed_at=test_run.completed_at,
        summary_metrics=test_run.summary_metrics,
        error_message=test_run.error_message,
        peak_vus=test_run.peak_vus,
        total_requests=test_run.total_requests,
        duration_seconds=test_run.duration_seconds,
        is_active=test_run.is_active,
        k6_script=test_run.k6_script,
        k6_options=test_run.k6_options,
        executor_info=test_run.executor_info,
        created_at=test_run.created_at,
        updated_at=test_run.updated_at,
    )


def _result_to_response(result: TestResult) -> TestResultResponse:
    """Convert TestResult model to response schema."""
    return TestResultResponse(
        id=result.id,
        timestamp=result.timestamp,
        metric_type=result.metric_type.value,
        metric_value=result.metric_value,
        percentile=result.percentile.value if result.percentile else None,
        tags=result.tags,
    )
