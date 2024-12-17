import sys
print(sys.path)
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from app.models.user_model import User, UserRole
from app.models.user_model import RetentionAnalytics
from app.services.analytics_service import AnalyticsService
from app.services.user_service import UserService

@pytest.mark.asyncio
async def test_log_user_activity():
    """Test updating the last login timestamp for a user."""
    mock_db = AsyncMock()
    user_id = uuid4()
    mock_user = User(id=user_id, last_login_at=None)
    mock_db.get.return_value = mock_user

    await AnalyticsService.log_user_activity(user_id, mock_db)

    assert mock_user.last_login_at is not None
    assert isinstance(mock_user.last_login_at, datetime)
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_calculate_total_users():
    """Test calculation of total anonymous and authenticated users."""
    mock_db = AsyncMock()
    mock_db.scalar.side_effect = [5, 10]  # 5 anonymous, 10 authenticated users

    await AnalyticsService.calculate_retention_metrics(mock_db)

    assert mock_db.scalar.call_count == 2  # Count both roles
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_calculate_conversion_rate():
    """Test calculation of user conversion rate."""
    mock_db = AsyncMock()
    mock_db.scalar.side_effect = [5, 10]  # 5 anonymous, 10 authenticated users

    await AnalyticsService.calculate_retention_metrics(mock_db)

    analytics_instance = mock_db.add.call_args[0][0]
    assert analytics_instance.conversion_rate == "66.67%"

@pytest.mark.asyncio
async def test_identify_inactive_users():
    """Test identifying inactive users across different time ranges."""
    mock_db = AsyncMock()
    now = datetime.now(timezone.utc)
    mock_db.scalar.side_effect = [
        3,  # 24-hour inactive
        7,  # 48-hour inactive
        15,  # 1-week inactive
        50,  # 1-year inactive
    ]

    await AnalyticsService.calculate_retention_metrics(mock_db)

    analytics_instance = mock_db.add.call_args[0][0]
    assert analytics_instance.inactive_users_24hr == 3
    assert analytics_instance.inactive_users_48hr == 7
    assert analytics_instance.inactive_users_1wk == 15
    assert analytics_instance.inactive_users_1yr == 50

@pytest.mark.asyncio
async def test_save_retention_analytics():
    """Test saving retention metrics to the database."""
    mock_db = AsyncMock()
    await AnalyticsService.calculate_retention_metrics(mock_db)

    mock_db.add.assert_called_once()
    analytics_instance = mock_db.add.call_args[0][0]
    assert isinstance(analytics_instance, RetentionAnalytics)

@pytest.mark.asyncio
async def test_get_retention_data():
    """Test retrieval of retention analytics data."""
    mock_db = AsyncMock()
    mock_retention_data = [RetentionAnalytics(timestamp=datetime.now(timezone.utc))]
    mock_db.execute.return_value.scalars.return_value = mock_retention_data

    data = await AnalyticsService.get_retention_data(mock_db)

    assert data is not None
    assert len(data.scalars().all()) == 1

@pytest.mark.asyncio
async def test_api_get_retention_metrics(async_client, mocker):
    """Test the /analytics/retention API endpoint."""
    mock_db = AsyncMock()
    mock_retention_data = [RetentionAnalytics(timestamp=datetime.now(timezone.utc))]
    mocker.patch("app.services.analytics_service.AnalyticsService.get_retention_data", return_value=mock_retention_data)

    response = await async_client.get("/analytics/retention")
    assert response.status_code == 200
    assert response.json() == {"data": mock_retention_data}


@pytest.mark.asyncio
async def test_invitation_validation_and_email_sending():
    """Test user invitation logic and email sending."""
    mock_db = AsyncMock()
    mock_email_service = AsyncMock()
    inviter_id = uuid4()
    email = "invitee@example.com"
    token = "invitation-token"

    mock_email_service.send_user_email = AsyncMock()

    # Simulate user invitation
    invitation_token = token
    user = User(email=email, invited_by_user_id=inviter_id, verification_token=invitation_token)
    mock_db.add(user)
    await mock_db.commit()

    assert mock_email_service.send_user_email.called

@pytest.mark.asyncio
async def test_registration_through_invitation():
    """Test user registration through invitation with a valid token."""
    mock_db = AsyncMock()
    mock_user = User(id=uuid4(), verification_token="valid-token", email_verified=False)
    mock_db.get.return_value = mock_user

    success = await UserService.verify_email_with_token(mock_db, mock_user.id, "valid-token")

    assert success is True
    assert mock_user.email_verified is True
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_edge_cases_empty_data():
    """Test edge case where no users are present in the database."""
    mock_db = AsyncMock()
    mock_db.scalar.side_effect = [0, 0]  # No anonymous or authenticated users

    await AnalyticsService.calculate_retention_metrics(mock_db)

    analytics_instance = mock_db.add.call_args[0][0]
    assert analytics_instance.total_anonymous_users == 0
    assert analytics_instance.total_authenticated_users == 0
    assert analytics_instance.conversion_rate == "0%"
