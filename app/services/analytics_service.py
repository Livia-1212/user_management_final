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
            now = datetime.now(timezone.utc)
            user.last_login_at = now
            db.add(user)
            await db.commit()

    @staticmethod
    async def calculate_retention_metrics(db: AsyncSession):
        """Calculate retention metrics and save them into the database."""
        now = datetime.now(timezone.utc)

        # Count total anonymous and authenticated users
        total_anonymous = await db.scalar(select(func.count()).where(User.role == "ANONYMOUS"))
        total_authenticated = await db.scalar(select(func.count()).where(User.role == "AUTHENTICATED"))

        # Calculate conversion rate
        conversion_rate = (
            f"{(total_authenticated / (total_anonymous + total_authenticated) * 100):.2f}%"
            if (total_anonymous + total_authenticated) > 0
            else "0%"
        )

        # Identify inactive users based on last login time
        inactive_24hr = await db.scalar(
            select(func.count()).where(User.last_login_at < now - timedelta(hours=24))
        )
        inactive_48hr = await db.scalar(
            select(func.count()).where(User.last_login_at < now - timedelta(hours=48))
        )
        inactive_1wk = await db.scalar(
            select(func.count()).where(User.last_login_at < now - timedelta(weeks=1))
        )
        inactive_1yr = await db.scalar(
            select(func.count()).where(User.last_login_at < now - timedelta(days=365))
        )

        # Construct and save analytics metrics
        analytics = RetentionAnalytics(
            total_anonymous_users=total_anonymous or 0,
            total_authenticated_users=total_authenticated or 0,
            conversion_rate=conversion_rate,
            inactive_users_24hr=inactive_24hr or 0,
            inactive_users_48hr=inactive_48hr or 0,
            inactive_users_1wk=inactive_1wk or 0,
            inactive_users_1yr=inactive_1yr or 0
        )

        db.add(analytics)
        await db.commit()

    @staticmethod
    async def get_retention_data(db: AsyncSession):
        """Retrieve the most recent retention analytics data."""
        result = await db.execute(
            RetentionAnalytics.__table__.select().order_by(RetentionAnalytics.timestamp.desc())
        )
        # Resolve the result to scalars and fetch all rows
        analytics_data = await result.scalars().all()
        return analytics_data
