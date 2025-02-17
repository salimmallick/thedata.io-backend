from typing import Optional, List, Dict, Any
from ..models.organization import (
    Organization,
    APIKey,
    RetentionPolicy,
    DataSource,
    UsageMetrics,
    OrganizationLimits,
    OnboardingStatus,
    SubscriptionTier,
    OrganizationStatus
)
from ..core.database import get_postgres_conn
import asyncpg
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class OrganizationService:
    """Service for managing customer organizations"""

    @staticmethod
    async def create_organization(
        name: str,
        slug: str,
        subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    ) -> Organization:
        """Create a new customer organization"""
        async with get_postgres_conn() as conn:
            # Check if slug is available
            existing = await conn.fetchval(
                "SELECT org_id FROM organizations WHERE slug = $1",
                slug
            )
            if existing:
                raise ValueError(f"Organization slug '{slug}' is already taken")

            # Create organization
            org_id = uuid.uuid4()
            now = datetime.utcnow()
            
            org = await conn.fetchrow("""
                INSERT INTO organizations (
                    org_id, name, slug, status, subscription_tier,
                    settings, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING *
                """,
                org_id,
                name,
                slug,
                OrganizationStatus.ACTIVE,
                subscription_tier,
                {},  # Default settings
                {},  # Default metadata
                now,
                now
            )

            # Create default retention policies
            limits = OrganizationLimits.get_tier_limits(subscription_tier)
            await RetentionPolicyService.create_default_policies(
                org_id,
                limits.max_retention_days
            )

            return Organization(**org)

    @staticmethod
    async def get_organization(org_id: uuid.UUID) -> Optional[Organization]:
        """Get organization by ID"""
        async with get_postgres_conn() as conn:
            org = await conn.fetchrow(
                "SELECT * FROM organizations WHERE org_id = $1",
                org_id
            )
            return Organization(**org) if org else None

    @staticmethod
    async def update_organization(
        org_id: uuid.UUID,
        updates: Dict[str, Any]
    ) -> Organization:
        """Update organization details"""
        async with get_postgres_conn() as conn:
            # Prepare update query
            set_clauses = []
            values = [org_id]
            for i, (key, value) in enumerate(updates.items(), start=2):
                set_clauses.append(f"{key} = ${i}")
                values.append(value)
            
            set_clauses.append("updated_at = $" + str(len(values) + 1))
            values.append(datetime.utcnow())

            query = f"""
                UPDATE organizations
                SET {', '.join(set_clauses)}
                WHERE org_id = $1
                RETURNING *
            """
            
            org = await conn.fetchrow(query, *values)
            return Organization(**org)

class APIKeyService:
    """Service for managing API keys"""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_api_key(key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    async def create_api_key(
        org_id: uuid.UUID,
        name: str,
        scopes: List[str],
        expires_in_days: Optional[int] = None
    ) -> tuple[APIKey, str]:
        """Create a new API key"""
        async with get_postgres_conn() as conn:
            # Check organization limits
            org = await OrganizationService.get_organization(org_id)
            limits = OrganizationLimits.get_tier_limits(org.subscription_tier)
            
            current_keys = await conn.fetchval(
                "SELECT COUNT(*) FROM api_keys WHERE org_id = $1 AND status = 'active'",
                org_id
            )
            
            if limits.max_api_keys != -1 and current_keys >= limits.max_api_keys:
                raise ValueError(f"Maximum number of API keys ({limits.max_api_keys}) reached")

            # Generate and store key
            key = APIKeyService.generate_api_key()
            key_hash = APIKeyService.hash_api_key(key)
            
            now = datetime.utcnow()
            expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None
            
            api_key = await conn.fetchrow("""
                INSERT INTO api_keys (
                    key_id, org_id, name, key_hash, scopes,
                    created_at, expires_at, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                uuid.uuid4(),
                org_id,
                name,
                key_hash,
                scopes,
                now,
                expires_at,
                'active'
            )
            
            return APIKey(**api_key), key

class RetentionPolicyService:
    """Service for managing data retention policies"""

    @staticmethod
    async def create_default_policies(
        org_id: uuid.UUID,
        max_retention_days: int
    ) -> List[RetentionPolicy]:
        """Create default retention policies for an organization"""
        default_policies = [
            ("user_interaction_events", max_retention_days),
            ("performance_events", min(max_retention_days, 90)),
            ("video_events", min(max_retention_days, 180)),
            ("log_events", min(max_retention_days, 30)),
            ("infrastructure_metrics", min(max_retention_days, 90))
        ]

        policies = []
        async with get_postgres_conn() as conn:
            for data_type, retention_days in default_policies:
                policy = await conn.fetchrow("""
                    INSERT INTO retention_policies (
                        policy_id, org_id, data_type, retention_days,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                    """,
                    uuid.uuid4(),
                    org_id,
                    data_type,
                    retention_days,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
                policies.append(RetentionPolicy(**policy))
        
        return policies

class OnboardingService:
    """Service for managing customer onboarding"""

    @staticmethod
    async def initialize_onboarding(org_id: uuid.UUID) -> OnboardingStatus:
        """Initialize onboarding process for a new organization"""
        async with get_postgres_conn() as conn:
            status = await conn.fetchrow("""
                INSERT INTO onboarding_status (
                    org_id,
                    steps_completed,
                    current_step,
                    integration_status,
                    data_sources_configured,
                    has_test_data,
                    has_production_data,
                    last_activity
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
                """,
                org_id,
                [],
                "welcome",
                {},
                0,
                False,
                False,
                datetime.utcnow()
            )
            return OnboardingStatus(**status)

    @staticmethod
    async def update_onboarding_progress(
        org_id: uuid.UUID,
        step_completed: str,
        next_step: str
    ) -> OnboardingStatus:
        """Update onboarding progress"""
        async with get_postgres_conn() as conn:
            status = await conn.fetchrow("""
                UPDATE onboarding_status
                SET steps_completed = array_append(steps_completed, $2),
                    current_step = $3,
                    last_activity = $4
                WHERE org_id = $1
                RETURNING *
                """,
                org_id,
                step_completed,
                next_step,
                datetime.utcnow()
            )
            return OnboardingStatus(**status)

# Create global service instances
organization_service = OrganizationService()
api_key_service = APIKeyService()
retention_policy_service = RetentionPolicyService()
onboarding_service = OnboardingService() 