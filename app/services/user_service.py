from builtins import Exception, bool, classmethod, int, str
from datetime import datetime, timezone
import secrets
from typing import Any, Optional, Dict, List
from pydantic import ValidationError
from sqlalchemy import func, null, update, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_email_service, get_settings
from app.models.user_model import User, UserRole
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.utils.nickname_gen import generate_nickname
from app.utils.security import generate_verification_token, hash_password, verify_password
from uuid import UUID
from pydantic import ValidationError
from app.services.email_service import EmailService
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

class UserService:
    @classmethod
    async def _execute_query(cls, session: AsyncSession, query):
        try:
            result = await session.execute(query)
            await session.commit()
            return result
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            await session.rollback()
            return None

    @classmethod
    async def _fetch_user(cls, session: AsyncSession, **filters) -> Optional[User]:
        query = select(User).filter_by(**filters)
        result = await cls._execute_query(session, query)
        return result.scalars().first() if result else None

    @classmethod
    async def get_by_id(cls, session: AsyncSession, user_id: UUID) -> Optional[User]:
        return await cls._fetch_user(session, id=user_id)

    @classmethod
    async def get_by_nickname(cls, session: AsyncSession, nickname: str) -> Optional[User]:
        return await cls._fetch_user(session, nickname=nickname)

    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: str) -> Optional[User]:
        return await cls._fetch_user(session, email=email)

    @classmethod
    async def create(cls, session: AsyncSession, user_data: Dict[str, str], email_service: EmailService) -> Optional[User]:
        try:
            validated_data = UserCreate(**user_data).model_dump()
            existing_user = await cls.get_by_email(session, validated_data['email'])
            if existing_user:
                logger.error("User with given email already exists.")
                return None
            
            # Hash the password
            validated_data['hashed_password'] = hash_password(validated_data.pop('password'))
            
            # Create user object
            new_user = User(**validated_data)

            # Generate a unique nickname
            new_nickname = generate_nickname()
            while await cls.get_by_nickname(session, new_nickname):
                new_nickname = generate_nickname()
            new_user.nickname = new_nickname

            # Assign role: First user as ADMIN, others as ANONYMOUS
            user_count = await cls.count(session)
            new_user.role = UserRole.ADMIN if user_count == 0 else UserRole.ANONYMOUS
            if new_user.role == UserRole.ADMIN:
                new_user.email_verified = True

            # Generate verification token
            new_user.verification_token = generate_verification_token()

            # Save to DB
            session.add(new_user)
            await session.commit()

            # Send verification email
            await email_service.send_verification_email(new_user)

            return new_user
        except ValidationError as e:
            logger.error(f"Validation error during user creation: {e}")
            return None

    @classmethod
    async def update(cls, session: AsyncSession, user_id: UUID, update_data: Dict[str, Optional[str]], current_user: dict) -> Optional[User]:
        """
        Updates user data, allowing role changes only by ADMIN users.

        Args:
            session: Database session.
            user_id: ID of the user to be updated.
            update_data: Data for the update (None values are ignored).
            current_user: User performing the update (must have ADMIN role for role changes).

        Returns:
            Updated user object or None if update fails.
        """
        try:
            # Step 1: Clean update_data by removing None values
            cleaned_data = {key: value for key, value in update_data.items() if value is not None}
            if not cleaned_data:
                logger.error("No valid fields provided for update.")
                return None

            # Step 2: Validate the cleaned data
            try:
                validated_data = UserUpdate(**cleaned_data).model_dump(exclude_unset=True)
            except ValidationError as e:
                logger.error(f"Validation error: {e}")
                return None

            logger.info(f"Updating user {user_id} with data: {validated_data}")

            # Step 3: Check role change permissions
            if 'role' in validated_data and current_user.get('role') != UserRole.ADMIN.name:
                logger.error("Unauthorized role update attempt.")
                return None

            # Step 4: Perform the update
            query = (
                update(User)
                .where(User.id == user_id)
                .values(**validated_data)
                .execution_options(synchronize_session="fetch")
            )
            result = await session.execute(query)
            await session.commit()

            # Step 5: Fetch and return the updated user
            if result.rowcount > 0:  # Ensure a row was updated
                updated_user = await cls.get_by_id(session, user_id)
                if updated_user:
                    session.refresh(updated_user)  # Ensure updated data
                    return updated_user

            logger.error(f"User {user_id} not found or update failed.")
            return None

        except Exception as e:
            logger.error(f"Error during user update: {e}")
            await session.rollback()
            return None


    @classmethod
    async def delete(cls, session: AsyncSession, user_id: UUID) -> bool:
        user = await cls.get_by_id(session, user_id)
        if not user:
            logger.info(f"User with ID {user_id} not found.")
            return False
        await session.delete(user)
        await session.commit()
        return True

    @classmethod
    async def list_users(cls, session: AsyncSession, skip: int = 0, limit: int = 10) -> List[User]:
        query = select(User).offset(skip).limit(limit)
        result = await cls._execute_query(session, query)
        return result.scalars().all() if result else []

    @classmethod
    async def register_user(cls, session: AsyncSession, user_data: Dict[str, str], get_email_service) -> Optional[User]:
        return await cls.create(session, user_data, get_email_service)
    

    @classmethod
    async def login_user(cls, session: AsyncSession, email: str, password: str) -> Optional[User]:
        user = await cls.get_by_email(session, email)
        if user:
            if user.email_verified is False:
                return None
            if user.is_locked:
                return None
            if verify_password(password, user.hashed_password):
                user.failed_login_attempts = 0
                user.last_login_at = datetime.now(timezone.utc)
                session.add(user)
                await session.commit()
                return user
            else:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= settings.max_login_attempts:
                    user.is_locked = True
                session.add(user)
                await session.commit()
        return None
    
    @classmethod
    async def invite_user(cls, session: AsyncSession, email: str, inviter_id: UUID, email_service: Any) -> bool:
        """
        Invite a new user by creating an invitation and sending an email.

        Args:
            session: Database session.
            email: Email address of the invitee.
            inviter_id: The ID of the user sending the invitation.
            email_service: Service for sending emails.

        Returns:
            True if the invitation was successfully sent, False otherwise.
        """
        try:
            # Generate a verification token
            invitation_token = generate_verification_token()
            
            # Create a new user with invited_by_user_id and token
            user = User(
                email=email,
                invited_by_user_id=inviter_id,
                verification_token=invitation_token
            )
            session.add(user)
            await session.commit()

            # Send the invitation email
            invite_link = f"{get_settings().server_base_url}/register?token={invitation_token}"
            await email_service.send_user_email(
                {"email": email, "invitation_link": invite_link}, "invitation"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to invite user: {e}")
            await session.rollback()
            return False

    @classmethod
    async def is_account_locked(cls, session: AsyncSession, email: str) -> bool:
        user = await cls.get_by_email(session, email)
        return user.is_locked if user else False


    @classmethod
    async def reset_password(cls, session: AsyncSession, user_id: UUID, new_password: str) -> bool:
        hashed_password = hash_password(new_password)
        user = await cls.get_by_id(session, user_id)
        if user:
            user.hashed_password = hashed_password
            user.failed_login_attempts = 0  # Resetting failed login attempts
            user.is_locked = False  # Unlocking the user account, if locked
            session.add(user)
            await session.commit()
            return True
        return False

    @classmethod
    async def verify_email_with_token(cls, session: AsyncSession, user_id: UUID, token: str) -> bool:
        user = await session.get(User, user_id)
        if user is None:
            return False
        
        if user.verification_token == token:
            user.email_verified = True
            user.verification_token = None  # Clear the token once used

            if user.role == UserRole.ANONYMOUS:
                user.role = UserRole.AUTHENTICATED

            session.add(user)
            await session.commit()  # Commit changes
            return True
        return False

    @classmethod
    async def count(cls, session: AsyncSession) -> int:
        """
        Count the number of users in the database.

        :param session: The AsyncSession instance for database access.
        :return: The count of users.
        """
        query = select(func.count()).select_from(User)
        result = await session.execute(query)
        count = result.scalar()
        return count
    
    @classmethod
    async def unlock_user_account(cls, session: AsyncSession, user_id: UUID) -> bool:
        user = await cls.get_by_id(session, user_id)
        if user and user.is_locked:
            user.is_locked = False
            user.failed_login_attempts = 0  # Optionally reset failed login attempts
            session.add(user)
            await session.commit()
            return True
        return False
