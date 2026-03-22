"""
Celery tasks package
"""

from src.tasks.billing_tasks import deduct_credits_async

__all__ = ["deduct_credits_async"]
