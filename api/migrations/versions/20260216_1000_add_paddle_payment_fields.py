"""add paddle payment provider fields

Revision ID: add_paddle_payment_fields
Revises: add_branding_colors
Create Date: 2026-02-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_paddle_payment_fields'
down_revision = 'add_branding_colors'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Paddle fields to subscription_plans table
    op.add_column(
        'subscription_plans',
        sa.Column('paddle_product_id', sa.String(255), nullable=True,
                  comment='Paddle Product ID for this plan')
    )
    op.add_column(
        'subscription_plans',
        sa.Column('paddle_price_id', sa.String(255), nullable=True,
                  comment='Paddle Price ID for monthly subscription')
    )

    # Add Paddle fields to tenant_subscriptions table
    op.add_column(
        'tenant_subscriptions',
        sa.Column('payment_provider', sa.String(20), nullable=False, server_default='stripe',
                  comment="Payment provider: 'stripe' or 'paddle'")
    )
    op.add_column(
        'tenant_subscriptions',
        sa.Column('paddle_subscription_id', sa.String(255), nullable=True,
                  comment='Paddle subscription ID for payment tracking')
    )
    op.add_column(
        'tenant_subscriptions',
        sa.Column('paddle_customer_id', sa.String(255), nullable=True,
                  comment='Paddle customer ID')
    )

    # Add indexes for tenant_subscriptions Paddle fields
    op.create_index(
        'ix_tenant_subscriptions_payment_provider',
        'tenant_subscriptions',
        ['payment_provider']
    )
    op.create_index(
        'ix_tenant_subscriptions_paddle_subscription_id',
        'tenant_subscriptions',
        ['paddle_subscription_id'],
        unique=True
    )
    op.create_index(
        'ix_tenant_subscriptions_paddle_customer_id',
        'tenant_subscriptions',
        ['paddle_customer_id']
    )

    # Add Paddle fields to credit_topups table
    op.add_column(
        'credit_topups',
        sa.Column('payment_provider', sa.String(20), nullable=False, server_default='stripe',
                  comment="Payment provider: 'stripe' or 'paddle'")
    )
    op.add_column(
        'credit_topups',
        sa.Column('paddle_transaction_id', sa.String(255), nullable=True,
                  comment='Paddle transaction ID')
    )

    # Add indexes for credit_topups Paddle fields
    op.create_index(
        'ix_credit_topups_payment_provider',
        'credit_topups',
        ['payment_provider']
    )
    op.create_index(
        'ix_credit_topups_paddle_transaction_id',
        'credit_topups',
        ['paddle_transaction_id'],
        unique=True
    )


def downgrade() -> None:
    # Remove indexes from credit_topups
    op.drop_index('ix_credit_topups_paddle_transaction_id', table_name='credit_topups')
    op.drop_index('ix_credit_topups_payment_provider', table_name='credit_topups')

    # Remove Paddle columns from credit_topups
    op.drop_column('credit_topups', 'paddle_transaction_id')
    op.drop_column('credit_topups', 'payment_provider')

    # Remove indexes from tenant_subscriptions
    op.drop_index('ix_tenant_subscriptions_paddle_customer_id', table_name='tenant_subscriptions')
    op.drop_index('ix_tenant_subscriptions_paddle_subscription_id', table_name='tenant_subscriptions')
    op.drop_index('ix_tenant_subscriptions_payment_provider', table_name='tenant_subscriptions')

    # Remove Paddle columns from tenant_subscriptions
    op.drop_column('tenant_subscriptions', 'paddle_customer_id')
    op.drop_column('tenant_subscriptions', 'paddle_subscription_id')
    op.drop_column('tenant_subscriptions', 'payment_provider')

    # Remove Paddle columns from subscription_plans
    op.drop_column('subscription_plans', 'paddle_price_id')
    op.drop_column('subscription_plans', 'paddle_product_id')
