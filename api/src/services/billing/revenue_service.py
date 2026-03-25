"""
Revenue Service - Manages revenue distribution and payout processing
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_pricing import AgentPricing
from src.models.agent_revenue import AgentRevenue, RevenueStatus
from src.models.credit_transaction import CreditTransaction
from src.models.tenant import Tenant
from src.services.billing.stripe_service import StripeService


class RevenueService:
    """Service for managing revenue distribution and payouts"""

    # Value of one credit in USD (e.g., $0.02)
    CREDIT_VALUE = Decimal("0.02")

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_revenue_by_id(self, revenue_id: UUID) -> AgentRevenue | None:
        """Get revenue record by ID"""
        result = await self.db.execute(select(AgentRevenue).where(AgentRevenue.id == revenue_id))
        return result.scalar_one_or_none()

    async def get_pending_payouts(
        self, tenant_id: UUID | None = None, min_amount: Decimal = Decimal("50.00")
    ) -> list[dict]:
        """Get pending payouts for creator tenants"""
        # Calculate amount from credits
        total_pending_credits = func.sum(AgentRevenue.creator_credits)

        # Build query
        query = (
            select(
                AgentRevenue.tenant_id,
                Tenant.name.label("tenant_name"),
                total_pending_credits.label("total_pending_credits"),
                func.count(AgentRevenue.id).label("transaction_count"),
                func.min(AgentRevenue.created_at).label("oldest_transaction"),
            )
            .join(Tenant, Tenant.id == AgentRevenue.tenant_id)
            .where(AgentRevenue.status == RevenueStatus.PENDING)
            .group_by(AgentRevenue.tenant_id, Tenant.name)
        )

        if tenant_id:
            query = query.where(AgentRevenue.tenant_id == tenant_id)

        result = await self.db.execute(query)
        rows = result.all()

        payouts = []
        for row in rows:
            pending_credits = int(row.total_pending_credits or 0)
            pending_amount = pending_credits * self.CREDIT_VALUE

            if pending_amount >= min_amount:
                payouts.append(
                    {
                        "tenant_id": str(row.tenant_id),
                        "tenant_name": row.tenant_name,
                        "total_pending_credits": pending_credits,
                        "total_pending_amount": float(pending_amount),
                        "transaction_count": int(row.transaction_count),
                        "oldest_transaction": row.oldest_transaction.isoformat(),
                    }
                )

        return payouts

    async def process_payout(
        self,
        tenant_id: UUID,  # Creator tenant ID
        stripe_account_id: str | None = None,
    ) -> dict:
        """Process payout for a creator tenant"""
        # Get pending revenue
        result = await self.db.execute(
            select(AgentRevenue).where(
                and_(AgentRevenue.tenant_id == tenant_id, AgentRevenue.status == RevenueStatus.PENDING)
            )
        )
        pending_revenues = list(result.scalars().all())

        if not pending_revenues:
            return {"success": False, "message": "No pending revenue to payout"}

        # Calculate total
        total_credits = sum(r.creator_credits for r in pending_revenues)
        total_amount = Decimal(total_credits) * self.CREDIT_VALUE

        # Minimum payout threshold
        if total_amount < Decimal("50.00"):
            return {"success": False, "message": f"Minimum payout amount is $50.00. Current balance: ${total_amount}"}

        try:
            payout_reference = f"PAYOUT-{uuid4()}"

            # Process Stripe payout if account ID provided
            if stripe_account_id:
                stripe_service = await StripeService.create(self.db)
                payout_result = await stripe_service.create_payout(
                    account_id=stripe_account_id,
                    amount_cents=int(total_amount * 100),  # Convert to cents
                )

                if not payout_result.get("success"):
                    return {"success": False, "message": f"Stripe payout failed: {payout_result.get('error')}"}

                # Use Stripe transfer ID if available
                if payout_result.get("id"):
                    payout_reference = payout_result.get("id")

            # Mark all revenues as paid
            payout_date = datetime.now(UTC)
            for revenue in pending_revenues:
                revenue.status = RevenueStatus.PAID
                revenue.payout_reference = payout_reference
                # revenue.updated_at will be updated automatically by ORM usually,
                # but if we want to query by payout time, relying on updated_at is okay if we just updated it.

            await self.db.commit()

            return {
                "success": True,
                "tenant_id": str(tenant_id),
                "amount": float(total_amount),
                "credits": total_credits,
                "transaction_count": len(pending_revenues),
                "payout_date": payout_date.isoformat(),
                "payout_reference": payout_reference,
            }

        except Exception as e:
            await self.db.rollback()
            return {"success": False, "message": f"Payout processing failed: {str(e)}"}

    async def get_revenue_analytics(
        self,
        agent_id: UUID | None = None,
        tenant_id: UUID | None = None,  # Creator tenant
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Get revenue analytics"""
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now(UTC)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Build base query conditions
        conditions = [AgentRevenue.created_at >= start_date, AgentRevenue.created_at <= end_date]

        # For agent_id, we need to join AgentPricing
        join_pricing = False
        if agent_id:
            join_pricing = True

        if tenant_id:
            conditions.append(AgentRevenue.tenant_id == tenant_id)

        # Get summary stats
        q_summary = select(
            func.sum(AgentRevenue.total_credits).label("total_credits"),
            func.sum(AgentRevenue.platform_credits).label("total_platform_credits"),
            func.sum(AgentRevenue.creator_credits).label("total_creator_credits"),
            func.count(AgentRevenue.id).label("total_transactions"),
            func.count(func.distinct(CreditTransaction.tenant_id)).label("unique_customers"),
        ).join(CreditTransaction, CreditTransaction.id == AgentRevenue.transaction_id)

        if join_pricing:
            q_summary = q_summary.join(AgentPricing, AgentPricing.id == AgentRevenue.agent_pricing_id)
            q_summary = q_summary.where(AgentPricing.agent_id == agent_id)

        q_summary = q_summary.where(and_(*conditions))

        result = await self.db.execute(q_summary)
        summary = result.first()

        # Get daily breakdown
        q_daily = select(
            func.date(AgentRevenue.created_at).label("date"),
            func.sum(AgentRevenue.total_credits).label("credits"),
            func.sum(AgentRevenue.creator_credits).label("creator_credits"),
            func.count(AgentRevenue.id).label("transactions"),
        )

        if join_pricing:
            q_daily = q_daily.join(AgentPricing, AgentPricing.id == AgentRevenue.agent_pricing_id)
            q_daily = q_daily.where(AgentPricing.agent_id == agent_id)

        q_daily = (
            q_daily.where(and_(*conditions))
            .group_by(func.date(AgentRevenue.created_at))
            .order_by(func.date(AgentRevenue.created_at))
        )

        daily_result = await self.db.execute(q_daily)
        daily_data = daily_result.all()

        # Calculate amounts
        total_credits = int(summary.total_credits or 0)
        total_revenue = float(Decimal(total_credits) * self.CREDIT_VALUE)

        creator_credits = int(summary.total_creator_credits or 0)
        total_creator_earnings = float(Decimal(creator_credits) * self.CREDIT_VALUE)

        platform_credits = int(summary.total_platform_credits or 0)
        total_platform_fee = float(Decimal(platform_credits) * self.CREDIT_VALUE)

        total_transactions = int(summary.total_transactions or 0)

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "summary": {
                "total_revenue": total_revenue,
                "total_platform_fee": total_platform_fee,
                "total_creator_earnings": total_creator_earnings,
                "total_credits": total_credits,
                "total_transactions": total_transactions,
                "unique_customers": int(summary.unique_customers or 0),
                "average_transaction": total_revenue / total_transactions if total_transactions else 0,
            },
            "daily_breakdown": [
                {
                    "date": row.date.isoformat(),
                    "revenue": float(Decimal(row.credits) * self.CREDIT_VALUE),
                    "earnings": float(Decimal(row.creator_credits) * self.CREDIT_VALUE),
                    "transactions": int(row.transactions),
                }
                for row in daily_data
            ],
        }

    async def get_top_customers(
        self,
        agent_id: UUID | None = None,
        tenant_id: UUID | None = None,  # Creator tenant
        limit: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """Get top customers by revenue"""
        # Default to last 30 days
        if not end_date:
            end_date = datetime.now(UTC)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Build conditions
        conditions = [AgentRevenue.created_at >= start_date, AgentRevenue.created_at <= end_date]

        if tenant_id:
            conditions.append(AgentRevenue.tenant_id == tenant_id)

        # Build query joining CreditTransaction to get consumer tenant
        query = (
            select(
                CreditTransaction.tenant_id,
                Tenant.name.label("tenant_name"),
                func.sum(AgentRevenue.total_credits).label("total_credits"),
                func.count(AgentRevenue.id).label("transaction_count"),
            )
            .join(CreditTransaction, CreditTransaction.id == AgentRevenue.transaction_id)
            .join(Tenant, Tenant.id == CreditTransaction.tenant_id)
        )

        if agent_id:
            query = query.join(AgentPricing, AgentPricing.id == AgentRevenue.agent_pricing_id)
            query = query.where(AgentPricing.agent_id == agent_id)

        query = (
            query.where(and_(*conditions))
            .group_by(CreditTransaction.tenant_id, Tenant.name)
            .order_by(func.sum(AgentRevenue.total_credits).desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "tenant_id": str(row.tenant_id),
                "tenant_name": row.tenant_name,
                "total_revenue": float(Decimal(row.total_credits) * self.CREDIT_VALUE),
                "total_credits": int(row.total_credits),
                "transaction_count": int(row.transaction_count),
            }
            for row in rows
        ]

    async def get_payout_history(
        self,
        tenant_id: UUID,  # Creator tenant ID
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Get payout history for a creator tenant"""
        # Get paid revenues grouped by payout reference
        query = (
            select(
                AgentRevenue.payout_reference,
                func.max(AgentRevenue.updated_at).label("payout_date"),
                func.sum(AgentRevenue.creator_credits).label("total_credits"),
                func.count(AgentRevenue.id).label("transaction_count"),
            )
            .where(
                and_(
                    AgentRevenue.tenant_id == tenant_id,
                    AgentRevenue.status == RevenueStatus.PAID,
                    AgentRevenue.payout_reference.isnot(None),
                )
            )
            .group_by(AgentRevenue.payout_reference)
            .order_by(func.max(AgentRevenue.updated_at).desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # Get total count
        count_query = select(func.count(func.distinct(AgentRevenue.payout_reference))).where(
            and_(
                AgentRevenue.tenant_id == tenant_id,
                AgentRevenue.status == RevenueStatus.PAID,
                AgentRevenue.payout_reference.isnot(None),
            )
        )
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()

        return {
            "tenant_id": str(tenant_id),
            "payouts": [
                {
                    "payout_reference": row.payout_reference,
                    "payout_date": row.payout_date.isoformat() if row.payout_date else None,
                    "amount": float(Decimal(row.total_credits) * self.CREDIT_VALUE),
                    "credits": int(row.total_credits),
                    "transaction_count": int(row.transaction_count),
                }
                for row in rows
            ],
            "total_count": int(total_count or 0),
            "limit": limit,
            "offset": offset,
        }

    async def mark_revenue_failed(self, revenue_id: UUID, reason: str) -> bool:
        """Mark a revenue record as failed"""
        revenue = await self.get_revenue_by_id(revenue_id)
        if not revenue:
            return False

        revenue.status = RevenueStatus.FAILED
        revenue.notes = reason
        await self.db.commit()
        return True
