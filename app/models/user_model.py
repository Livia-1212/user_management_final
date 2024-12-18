from builtins import bool, int, str
from datetime import datetime, timezone
from enum import Enum
import uuid
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, func, Enum as SQLAlchemyEnum, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class UserRole(Enum):
    """Enumeration of user roles within the application, stored as ENUM in the database."""
    ANONYMOUS = "ANONYMOUS"
    AUTHENTICATED = "AUTHENTICATED"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"

class User(Base):
    """
    Represents a user within the application, corresponding to the 'users' table in the database.
    This class uses SQLAlchemy ORM for mapping attributes to database columns efficiently.
    
    Attributes:
        id (UUID): Unique identifier for the user.
        nickname (str): Unique nickname for privacy, required.
        email (str): Unique email address, required.
        email_verified (bool): Flag indicating if the email has been verified.
        hashed_password (str): Hashed password for security, required.
        first_name (str): Optional first name of the user.
        last_name (str): Optional first name of the user.

        bio (str): Optional biographical information.
        profile_picture_url (str): Optional URL to a profile picture.
        linkedin_profile_url (str): Optional LinkedIn profile URL.
        github_profile_url (str): Optional GitHub profile URL.
        role (UserRole): Role of the user within the application.
        is_professional (bool): Flag indicating professional status.
        professional_status_updated_at (datetime): Timestamp of last professional status update.
        last_login_at (datetime): Timestamp of the last login.
        failed_login_attempts (int): Count of failed login attempts.
        is_locked (bool): Flag indicating if the account is locked.
        created_at (datetime): Timestamp when the user was created, set by the server.
        updated_at (datetime): Timestamp of the last update, set by the server.

    Methods:
        lock_account(): Locks the user account.
        unlock_account(): Unlocks the user account.
        verify_email(): Marks the user's email as verified.
        has_role(role_name): Checks if the user has a specified role.
        update_professional_status(status): Updates the professional status and logs the update time.
    """
    __tablename__ = "users"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname: Mapped[str] = Column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = Column(String(100), nullable=True)
    last_name: Mapped[str] = Column(String(100), nullable=True)
    bio: Mapped[str] = Column(String(500), nullable=True)
    profile_picture_url: Mapped[str] = Column(String(255), nullable=True)
    linkedin_profile_url: Mapped[str] = Column(String(255), nullable=True)
    github_profile_url: Mapped[str] = Column(String(255), nullable=True)
    role: Mapped[UserRole] = Column(SQLAlchemyEnum(UserRole, name='UserRole', create_constraint=True), nullable=False)
    is_professional: Mapped[bool] = Column(Boolean, default=False)
    professional_status_updated_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = Column(Integer, default=0)
    is_locked: Mapped[bool] = Column(Boolean, default=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    verification_token = Column(String, nullable=True)
    email_verified: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    hashed_password: Mapped[str] = Column(String(255), nullable=False)
     # New fields for retention analytics
    invited_by_user_id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invited_by = relationship("User", remote_side="User.id", backref="invited_users")
    is_converted: Mapped[bool] = Column(Boolean, default=False)


    def __repr__(self) -> str:
        """Provides a readable representation of a user object."""
        return f"<User {self.nickname}, Role: {self.role.name}>"

    def lock_account(self):
        self.is_locked = True

    def unlock_account(self):
        self.is_locked = False

    def verify_email(self):
        self.email_verified = True

    def has_role(self, role_name: UserRole) -> bool:
        return self.role == role_name

    def update_professional_status(self, status: bool):
        """Updates the professional status and logs the update time."""
        self.is_professional = status
        self.professional_status_updated_at = func.now()

    # New feature of retention analytics
    def update_last_login(self):
        """Updates the last login timestamp."""
        self.last_login_at = datetime.now(timezone.utc)


class RetentionAnalytics(Base):
    """
    Tracks user retention analytics.
    """
    __tablename__ = "retention_analytics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    total_anonymous_users: Mapped[int] = Column(Integer, default=0)
    total_authenticated_users: Mapped[int] = Column(Integer, default=0)
    conversion_rate: Mapped[str] = Column(String(10), nullable=False)  # Example: "20%"
    inactive_users_24hr: Mapped[int] = Column(Integer, default=0)

    def __repr__(self):
        """Provides a readable representation of analytics data."""
        return (
            f"<RetentionAnalytics {self.timestamp}: "
            f"Anonymous={self.total_anonymous_users}, "
            f"Authenticated={self.total_authenticated_users}, "
            f"Conversion={self.conversion_rate}>"
        )