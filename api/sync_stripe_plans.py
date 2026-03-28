#!/usr/bin/env python3
"""
Sync subscription plans with Stripe products and prices.
This script creates Stripe products and prices for existing subscription plans
and updates the database with the Stripe IDs.
"""

import asyncio
import sys

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session_factory
from src.models.subscription_plan import PlanTier, SubscriptionPlan
from src.services.integrations.integration_config_service import IntegrationConfigService


async def get_stripe_key(db: AsyncSession) -> str:
    """Get Stripe secret key from integration settings"""
    integration_service = IntegrationConfigService(db)

    config = await integration_service.get_active_config(None, "payment", "stripe")

    if not config:
        print("❌ Error: Stripe integration not configured")
        print("   Please configure Stripe integration at: /settings/integrations/payment/create")
        sys.exit(1)

    config_data = integration_service._decrypt_config(config.config_data)
    credentials = config_data.get("credentials", {})
    stripe_key = credentials.get("secret_key")

    if not stripe_key:
        print("❌ Error: Stripe secret key not found in integration configuration")
        print("   Please configure Stripe integration at: /settings/integrations/payment/create")
        sys.exit(1)

    return stripe_key


async def sync_stripe_plans_async(db: AsyncSession, force: bool = False) -> None:
    """Sync subscription plans with Stripe."""
    stripe_key = await get_stripe_key(db)
    stripe.api_key = stripe_key

    print("🔄 Syncing subscription plans with Stripe...\n")

    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.tier != PlanTier.FREE)
    )
    plans = result.scalars().all()

    if not plans:
        print("⚠️  No subscription plans found in database")
        return

    synced_count = 0
    skipped_count = 0
    error_count = 0

    for plan in plans:
        try:
            if plan.stripe_product_id and plan.stripe_price_id and not force:
                print(f"⏭️  Skipping {plan.name} - already configured")
                print(f"   Product ID: {plan.stripe_product_id}")
                print(f"   Price ID: {plan.stripe_price_id}\n")
                skipped_count += 1
                continue

            print(f"🔧 Processing {plan.name} ({plan.tier.value})...")

            if plan.stripe_product_id and force:
                product = stripe.Product.modify(
                    plan.stripe_product_id,
                    name=plan.name,
                    description=plan.description,
                    metadata={"tier": plan.tier.value, "plan_id": str(plan.id)},
                )
                print(f"   ✓ Updated Stripe product: {product.id}")
            else:
                product = stripe.Product.create(
                    name=plan.name,
                    description=plan.description,
                    metadata={"tier": plan.tier.value, "plan_id": str(plan.id)},
                )
                print(f"   ✓ Created Stripe product: {product.id}")

            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(plan.price_monthly * 100),
                currency="usd",
                recurring={"interval": "month"},
                metadata={"tier": plan.tier.value, "billing_period": "monthly", "plan_id": str(plan.id)},
            )
            print(f"   ✓ Created monthly price: {price.id} (${plan.price_monthly}/month)")

            yearly_price = stripe.Price.create(
                product=product.id,
                unit_amount=int(plan.price_yearly * 100),
                currency="usd",
                recurring={"interval": "year"},
                metadata={"tier": plan.tier.value, "billing_period": "yearly", "plan_id": str(plan.id)},
            )
            print(f"   ✓ Created yearly price: {yearly_price.id} (${plan.price_yearly}/year)")

            plan.stripe_product_id = product.id
            plan.stripe_price_id = price.id

            print("   ✓ Updated database with Stripe IDs\n")
            synced_count += 1

        except stripe.error.StripeError as e:
            print(f"   ❌ Stripe error for {plan.name}: {str(e)}\n")
            error_count += 1
        except Exception as e:
            print(f"   ❌ Error processing {plan.name}: {str(e)}\n")
            error_count += 1

    try:
        await db.commit()
        print("=" * 60)
        print("✅ Sync complete!")
        print(f"   Synced: {synced_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Errors: {error_count}")
        print("=" * 60)
    except Exception as e:
        await db.rollback()
        print(f"❌ Error committing changes: {str(e)}")
        sys.exit(1)


async def verify_sync_async(db: AsyncSession) -> None:
    """Verify that all plans are properly synced"""
    print("\n🔍 Verifying sync status...\n")

    result = await db.execute(select(SubscriptionPlan))
    plans = result.scalars().all()

    for plan in plans:
        if plan.tier == PlanTier.FREE:
            print(f"✓ {plan.name} (FREE) - No Stripe sync required")
        elif plan.stripe_product_id and plan.stripe_price_id:
            print(f"✓ {plan.name} ({plan.tier.value})")
            print(f"  Product: {plan.stripe_product_id}")
            print(f"  Price: {plan.stripe_price_id}")
        else:
            print(f"❌ {plan.name} ({plan.tier.value}) - Missing Stripe IDs")


async def run(force: bool = False, verify_only: bool = False) -> None:
    """Single entry point — one event loop, one session."""
    factory = get_async_session_factory()
    async with factory() as db:
        if not verify_only:
            await sync_stripe_plans_async(db, force=force)
        await verify_sync_async(db)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sync subscription plans with Stripe")
    parser.add_argument("--force", action="store_true", help="Force recreation of Stripe products even if they exist")
    parser.add_argument("--verify", action="store_true", help="Only verify sync status without making changes")

    args = parser.parse_args()
    asyncio.run(run(force=args.force, verify_only=args.verify))


if __name__ == "__main__":
    main()
