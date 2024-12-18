import sys
print(sys.path)
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
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
    
    # Simulate scalar() results: total_anonymous = 5, total_authenticated = 10
    mock_db.scalar.side_effect = [5, 10, 3, 7, 15, 50]  # Counts for different metrics
    
    # Call the service method
    await AnalyticsService.calculate_retention_metrics(mock_db)
    
    # Verify RetentionAnalytics object was added
    analytics_instance = mock_db.add.call_args[0][0]
    assert analytics_instance.total_anonymous_users == 5
    assert analytics_instance.total_authenticated_users == 10
    assert analytics_instance.conversion_rate == "66.67%"
    assert analytics_instance.inactive_users_24hr == 3
    assert analytics_instance.inactive_users_48hr == 7
    assert analytics_instance.inactive_users_1wk == 15
    assert analytics_instance.inactive_users_1yr == 50

    # Ensure that commit() was called
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_retention_data():
    """Test retrieval of retention analytics data."""
    # Mock database session
    mock_db = AsyncMock()

    # Define the mock retention data
    mock_retention_data = [RetentionAnalytics(timestamp=datetime.now(timezone.utc))]

    # Mock the result of `execute`
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = mock_retention_data  # Mock scalars().all()
    mock_db.execute.return_value = mock_result  # db.execute() returns mock_result

    # Call the service method
    data = await AnalyticsService.get_retention_data(mock_db)

    # Assertions
    assert data == mock_retention_data
    mock_db.execute.assert_called_once()
    mock_result.scalars.assert_called_once()



@pytest.mark.asyncio
async def test_api_get_retention_metrics(async_client, mocker):
    """Test the /analytics/retention API endpoint."""
    # Prepare the mock retention analytics data
    mock_retention_data = [
        RetentionAnalytics(timestamp=datetime.now(timezone.utc))
    ]

    # Simplified serialized data matching the API's response structure
    serialized_data = [
        {"timestamp": ra.timestamp.isoformat()}
        for ra in mock_retention_data
    ]

    # Patch the service method to return mock data
    mocker.patch(
        "app.services.analytics_service.AnalyticsService.get_retention_data",
        return_value=mock_retention_data
    )

    # Call the API endpoint
    response = await async_client.get("/analytics/retention")

    # Verify the response
    assert response.status_code == 200
    assert response.json() == {"data": serialized_data}


@pytest.mark.asyncio
async def test_invitation_validation_and_email_sending():
    """Test user invitation logic and email sending."""
    mock_db = AsyncMock()
    mock_email_service = AsyncMock()
    inviter_id = uuid4()
    email = "invitee@example.com"

    # Call the actual invite_user service method
    await UserService.invite_user(
        session=mock_db,
        email=email,
        inviter_id=inviter_id,
        email_service=mock_email_service
    )

    # Verify email was sent
    mock_email_service.send_user_email.assert_called_once()
    mock_db.add.assert_called_once()  # Ensure the user was added to the database
    mock_db.commit.assert_called_once()  # Ensure the commit was performed

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

    # Provide six zeros for all scalar calls
    mock_db.scalar.side_effect = [0, 0, 0, 0, 0, 0]  

    await AnalyticsService.calculate_retention_metrics(mock_db)

    analytics_instance = mock_db.add.call_args[0][0]
    assert analytics_instance.total_anonymous_users == 0
    assert analytics_instance.total_authenticated_users == 0
    assert analytics_instance.conversion_rate == "0%"
    assert analytics_instance.inactive_users_24hr == 0
    assert analytics_instance.inactive_users_48hr == 0
    assert analytics_instance.inactive_users_1wk == 0
    assert analytics_instance.inactive_users_1yr == 0

    # Ensure commit was called
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_handle_missing_last_login_timestamps():
    """Test retention analytics when some users have no last login timestamps."""
    mock_db = AsyncMock()

    # Mock users with missing last_login_at timestamps
    mock_db.scalar.side_effect = [
        10,  # Total anonymous users
        20,  # Total authenticated users
        0,   # Inactive users in the last 24 hours
    ]

    await AnalyticsService.calculate_retention_metrics(mock_db)

    # Verify retention analytics instance created
    analytics_instance = mock_db.add.call_args[0][0]
    assert analytics_instance.total_anonymous_users == 10
    assert analytics_instance.total_authenticated_users == 20
    assert analytics_instance.conversion_rate == "66.67%"
    assert analytics_instance.inactive_users_24hr == 0

    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_large_user_counts():
    """Test retention analytics with large numbers of users to ensure scalability."""
    mock_db = AsyncMock()

    # Simulate large numbers of users
    mock_db.scalar.side_effect = [
        1_000_000,  # Total anonymous users
        2_000_000,  # Total authenticated users
        500_000,    # Inactive users in the last 24 hours
    ]

    await AnalyticsService.calculate_retention_metrics(mock_db)

    # Verify retention analytics instance created
    analytics_instance = mock_db.add.call_args[0][0]
    assert analytics_instance.total_anonymous_users == 1_000_000
    assert analytics_instance.total_authenticated_users == 2_000_000
    assert analytics_instance.conversion_rate == "66.67%"
    assert analytics_instance.inactive_users_24hr == 500_000

    mock_db.commit.assert_called_once()
