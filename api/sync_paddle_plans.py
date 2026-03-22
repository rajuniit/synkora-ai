#!/usr/bin/env python3
"""
Sync subscription plans with Paddle products and prices.
This script creates Paddle products and prices for existing subscription plans
and updates the database with the Paddle IDs.

Paddle API Documentation: https://developer.paddle.com/api-reference/overview
"""

import asyncio
import sys

import httpx
from sqlalchemy.orm import Session

from src.core.database import SessionLocal, get_async_session_factory
from src.models.subscription_plan import PlanTier, SubscriptionPlan
from src.services.integrations.integration_config_service import IntegrationConfigService


class PaddleAPI:
    """Simple Paddle API client for product and price management"""

    def __init__(self, api_key: str, environment: str = "sandbox"):
        self.api_key = api_key
        self.environment = environment
        self.base_url = "https://sandbox-api.paddle.com" if environment == "sandbox" else "https://api.paddle.com"

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, endpoint: str, data: dict | None = None, params: dict | None = None) -> dict:
        """Make an authenticated request to Paddle API"""
        url = f"{self.base_url}{endpoint}"

        with httpx.Client() as client:
            response = client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=data,
                params=params,
                timeout=30.0,
            )

            if response.status_code >= 400:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("detail", response.text)
                raise Exception(f"Paddle API error ({response.status_code}): {error_msg}")

            return response.json() if response.content else {}

    def list_products(self) -> list[dict]:
        """List all products"""
        response = self._make_request("GET", "/products")
        return response.get("data", [])

    def create_product(
        self,
        name: str,
        description: str | None = None,
        tax_category: str = "standard",
        custom_data: dict | None = None,
    ) -> dict:
        """
        Create a new product in Paddle

        Args:
            name: Product name
            description: Product description
            tax_category: Tax category (standard, digital-goods, ebooks, etc.)
            custom_data: Custom metadata

        Returns:
            Product data with ID
        """
        data = {
            "name": name,
            "tax_category": tax_category,
        }

        if description:
            data["description"] = description

        if custom_data:
            data["custom_data"] = custom_data

        response = self._make_request("POST", "/products", data=data)
        return response.get("data", {})

    def update_product(
        self,
        product_id: str,
        name: str | None = None,
        description: str | None = None,
        custom_data: dict | None = None,
    ) -> dict:
        """Update an existing product"""
        data = {}

        if name:
            data["name"] = name
        if description:
            data["description"] = description
        if custom_data:
            data["custom_data"] = custom_data

        response = self._make_request("PATCH", f"/products/{product_id}", data=data)
        return response.get("data", {})

    def list_prices(self, product_id: str | None = None) -> list[dict]:
        """List all prices, optionally filtered by product"""
        params = {}
        if product_id:
            params["product_id"] = product_id

        response = self._make_request("GET", "/prices", params=params)
        return response.get("data", [])

    def create_price(
        self,
        product_id: str,
        unit_price_amount: int,
        unit_price_currency: str = "USD",
        description: str | None = None,
        billing_cycle_interval: str = "month",
        billing_cycle_frequency: int = 1,
        trial_period_days: int | None = None,
        custom_data: dict | None = None,
    ) -> dict:
        """
        Create a new price for a product

        Args:
            product_id: Product ID to attach price to
            unit_price_amount: Price amount in smallest currency unit (e.g., cents)
            unit_price_currency: Currency code (USD, EUR, etc.)
            description: Price description
            billing_cycle_interval: day, week, month, year
            billing_cycle_frequency: Number of intervals (1 = monthly, 12 = annually for month)
            trial_period_days: Trial period in days
            custom_data: Custom metadata

        Returns:
            Price data with ID
        """
        data = {
            "product_id": product_id,
            "unit_price": {
                "amount": str(unit_price_amount),
                "currency_code": unit_price_currency,
            },
            "billing_cycle": {
                "interval": billing_cycle_interval,
                "frequency": billing_cycle_frequency,
            },
        }

        if description:
            data["description"] = description

        if trial_period_days:
            data["trial_period"] = {
                "interval": "day",
                "frequency": trial_period_days,
            }

        if custom_data:
            data["custom_data"] = custom_data

        response = self._make_request("POST", "/prices", data=data)
        return response.get("data", {})

    def archive_price(self, price_id: str) -> dict:
        """Archive a price (soft delete)"""
        data = {"status": "archived"}
        response = self._make_request("PATCH", f"/prices/{price_id}", data=data)
        return response.get("data", {})


async def get_paddle_config() -> tuple[str, str]:
    """Get Paddle API key and environment from integration settings"""
    session_factory = get_async_session_factory()
    async with session_factory() as async_db:
        integration_service = IntegrationConfigService(async_db)

        # Get active Paddle integration config (platform-wide, tenant_id=None)
        config = await integration_service.get_active_config(None, "payment", "paddle")

        if not config:
            print("❌ Error: Paddle integration not configured")
            print("   Please configure Paddle integration at: /settings/integrations/payment/create")
            sys.exit(1)

        # Decrypt config data
        config_data = integration_service._decrypt_config(config.config_data)

    # Extract API key from credentials
    credentials = config_data.get("credentials", {})
    api_key = credentials.get("api_key")

    if not api_key:
        print("❌ Error: Paddle API key not found in integration configuration")
        print("   Please configure Paddle integration at: /settings/integrations/payment/create")
        sys.exit(1)

    # Get environment
    settings = config_data.get("settings", {})
    environment = settings.get("environment", "sandbox")

    return api_key, environment


async def sync_paddle_plans_async(db: Session, force: bool = False) -> None:
    """
    Sync subscription plans with Paddle.

    Args:
        db: Database session
        force: If True, recreate Paddle products even if they already exist
    """
    # Get Paddle credentials from integration settings
    api_key, environment = await get_paddle_config()
    paddle = PaddleAPI(api_key, environment)

    print(f"🔄 Syncing subscription plans with Paddle ({environment})...\n")

    # Get all plans except FREE tier
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.tier != PlanTier.FREE).all()

    if not plans:
        print("⚠️  No subscription plans found in database")
        return

    synced_count = 0
    skipped_count = 0
    error_count = 0

    for plan in plans:
        try:
            # Skip if already configured and not forcing
            if plan.paddle_product_id and plan.paddle_price_id and not force:
                print(f"⏭️  Skipping {plan.name} - already configured")
                print(f"   Product ID: {plan.paddle_product_id}")
                print(f"   Price ID: {plan.paddle_price_id}\n")
                skipped_count += 1
                continue

            print(f"🔧 Processing {plan.name} ({plan.tier.value})...")

            # Create or update Paddle product
            if plan.paddle_product_id and force:
                # Update existing product
                product = paddle.update_product(
                    plan.paddle_product_id,
                    name=plan.name,
                    description=plan.description,
                    custom_data={"tier": plan.tier.value, "plan_id": str(plan.id)},
                )
                print(f"   ✓ Updated Paddle product: {product['id']}")
            else:
                # Create new product
                product = paddle.create_product(
                    name=plan.name,
                    description=plan.description or f"{plan.name} subscription plan",
                    tax_category="standard",  # Use 'digital-goods' for digital products
                    custom_data={"tier": plan.tier.value, "plan_id": str(plan.id)},
                )
                print(f"   ✓ Created Paddle product: {product['id']}")

            # Create monthly price
            price = paddle.create_price(
                product_id=product["id"],
                unit_price_amount=int(plan.price_monthly * 100),  # Convert to cents
                unit_price_currency="USD",
                description=f"{plan.name} - Monthly",
                billing_cycle_interval="month",
                billing_cycle_frequency=1,
                custom_data={
                    "tier": plan.tier.value,
                    "billing_period": "monthly",
                    "plan_id": str(plan.id),
                },
            )
            print(f"   ✓ Created monthly price: {price['id']} (${plan.price_monthly}/month)")

            # Create yearly price (optional, for future use)
            if plan.price_yearly:
                yearly_price = paddle.create_price(
                    product_id=product["id"],
                    unit_price_amount=int(plan.price_yearly * 100),  # Convert to cents
                    unit_price_currency="USD",
                    description=f"{plan.name} - Yearly",
                    billing_cycle_interval="year",
                    billing_cycle_frequency=1,
                    custom_data={
                        "tier": plan.tier.value,
                        "billing_period": "yearly",
                        "plan_id": str(plan.id),
                    },
                )
                print(f"   ✓ Created yearly price: {yearly_price['id']} (${plan.price_yearly}/year)")

            # Update plan with Paddle IDs
            plan.paddle_product_id = product["id"]
            plan.paddle_price_id = price["id"]  # Default to monthly price

            print("   ✓ Updated database with Paddle IDs\n")
            synced_count += 1

        except Exception as e:
            print(f"   ❌ Error processing {plan.name}: {str(e)}\n")
            error_count += 1

    # Commit all changes
    try:
        db.commit()
        print("=" * 60)
        print("✅ Sync complete!")
        print(f"   Synced: {synced_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Errors: {error_count}")
        print("=" * 60)
    except Exception as e:
        db.rollback()
        print(f"❌ Error committing changes: {str(e)}")
        sys.exit(1)


def sync_paddle_plans(db: Session, force: bool = False) -> None:
    """Synchronous wrapper for async sync function"""
    asyncio.run(sync_paddle_plans_async(db, force))


def verify_sync(db: Session) -> None:
    """Verify that all plans are properly synced with Paddle"""
    print("\n🔍 Verifying Paddle sync status...\n")

    plans = db.query(SubscriptionPlan).all()

    for plan in plans:
        if plan.tier == PlanTier.FREE:
            print(f"✓ {plan.name} (FREE) - No Paddle sync required")
        elif plan.paddle_product_id and plan.paddle_price_id:
            print(f"✓ {plan.name} ({plan.tier.value})")
            print(f"  Product: {plan.paddle_product_id}")
            print(f"  Price: {plan.paddle_price_id}")
        else:
            print(f"❌ {plan.name} ({plan.tier.value}) - Missing Paddle IDs")


def list_paddle_products(db: Session) -> None:
    """List all products in Paddle"""
    print("\n📦 Listing Paddle products...\n")

    api_key, environment = asyncio.run(get_paddle_config())
    paddle = PaddleAPI(api_key, environment)

    try:
        products = paddle.list_products()
        if not products:
            print("No products found in Paddle")
            return

        for product in products:
            print(f"Product: {product['name']}")
            print(f"  ID: {product['id']}")
            print(f"  Status: {product.get('status', 'unknown')}")
            print(f"  Tax Category: {product.get('tax_category', 'unknown')}")

            # List prices for this product
            prices = paddle.list_prices(product["id"])
            for price in prices:
                unit_price = price.get("unit_price", {})
                billing_cycle = price.get("billing_cycle", {})
                print(
                    f"  Price: {price['id']} - "
                    f"{unit_price.get('amount', 'N/A')} {unit_price.get('currency_code', 'USD')}/"
                    f"{billing_cycle.get('interval', 'month')}"
                )
            print()

    except Exception as e:
        print(f"❌ Error listing products: {str(e)}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Sync subscription plans with Paddle")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreation of Paddle products even if they exist",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify sync status without making changes",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all products in Paddle",
    )

    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.list:
            list_paddle_products(db)
        elif args.verify:
            verify_sync(db)
        else:
            sync_paddle_plans(db, force=args.force)
            verify_sync(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
