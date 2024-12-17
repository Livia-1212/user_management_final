from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func, select
from datetime import datetime, timezone, timedelta
from app.models.user_model import User, RetentionAnalytics
from uuid import UUID


class AnalyticsService:
    @staticmethod
    async def log_user_activity(user_id: UUID, db: AsyncSession):
        """Update the last login timestamp for a user."""
        user = await db.get(User, user_id)
        if user:
            now = datetime.now(timezone.utc)  # Corrected 'datetime'
            user.last_login_at = now
            db.add(user)
            await db.commit()


    @staticmethod
    async def calculate_retention_metrics(db: AsyncSession):
        """Calculate retention metrics and save them into the database."""
        now = datetime.now(timezone.utc)

        # Count total anonymous and authenticated users using select()
        total_anonymous = await db.scalar(select(func.count()).where(User.role == "ANONYMOUS"))
        total_authenticated = await db.scalar(select(func.count()).where(User.role == "AUTHENTICATED"))

        # Calculate conversion rate
        conversion_rate = (
            f"{(total_authenticated / (total_anonymous + total_authenticated) * 100):.2f}%"
            if (total_anonymous + total_authenticated) > 0
            else "0%"
        )

        # Save the metrics to RetentionAnalytics
        analytics = RetentionAnalytics(
            total_anonymous_users=total_anonymous,
            total_authenticated_users=total_authenticated,
            conversion_rate=conversion_rate,
            timestamp=now,
        )
        db.add(analytics)
        await db.commit()


    @staticmethod
    async def get_retention_data(db: AsyncSession):
        """Retrieve the most recent retention analytics data."""
        query = await db.execute(
            RetentionAnalytics.__table__.select().order_by(RetentionAnalytics.timestamp.desc())
        )
        return query.scalars().all()
