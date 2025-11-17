"""
Authentication service
Handles user registration, login, password hashing, and session management
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

from models.user import User, UserCreate, UserLogin, Session

logger = logging.getLogger(__name__)


class AuthService:
    """Service for user authentication and session management"""

    def __init__(self, storage):
        """
        Initialize auth service

        Args:
            storage: DynamoDBStorage instance for user data
        """
        self.storage = storage
        self.sessions: Dict[str, Session] = {}  # In-memory sessions (can be moved to Redis/DynamoDB)
        self.session_duration = timedelta(hours=24)  # Session expires after 24 hours

    def hash_password(self, password: str) -> str:
        """
        Hash password using SHA-256 with salt

        Args:
            password: Plain text password

        Returns:
            Hashed password with salt
        """
        # Generate a random salt
        salt = secrets.token_hex(16)

        # Hash password with salt
        password_hash = hashlib.sha256((salt + password).encode()).hexdigest()

        # Return salt + hash (first 32 chars = salt, rest = hash)
        return f"{salt}{password_hash}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash

        Args:
            password: Plain text password to verify
            password_hash: Stored password hash with salt

        Returns:
            True if password matches
        """
        # Extract salt (first 32 characters)
        salt = password_hash[:32]
        stored_hash = password_hash[32:]

        # Hash input password with same salt
        input_hash = hashlib.sha256((salt + password).encode()).hexdigest()

        return input_hash == stored_hash

    async def register_user(self, user_create: UserCreate) -> Optional[User]:
        """
        Register a new user

        Args:
            user_create: User registration data

        Returns:
            Created User object or None if username exists
        """
        try:
            # Check if username already exists
            existing_user = await self.storage.get_user(user_create.username)
            if existing_user:
                logger.warning(f"Username already exists: {user_create.username}")
                return None

            # Hash password
            password_hash = self.hash_password(user_create.password)

            # Create user object
            user = User(
                username=user_create.username.lower(),
                email=user_create.email,
                password_hash=password_hash,
                full_name=user_create.full_name,
                created_at=datetime.now(),
                is_active=True
            )

            # Save to database
            success = await self.storage.save_user(user)
            if success:
                logger.info(f"User registered successfully: {user.username}")
                return user
            else:
                logger.error(f"Failed to save user: {user.username}")
                return None

        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return None

    async def login(self, user_login: UserLogin) -> Optional[Session]:
        """
        Authenticate user and create session

        Args:
            user_login: Login credentials

        Returns:
            Session object if login successful, None otherwise
        """
        try:
            # Get user from database
            user = await self.storage.get_user(user_login.username.lower())
            if not user:
                logger.warning(f"User not found: {user_login.username}")
                return None

            # Check if user is active
            if not user.is_active:
                logger.warning(f"User account is inactive: {user_login.username}")
                return None

            # Verify password
            if not self.verify_password(user_login.password, user.password_hash):
                logger.warning(f"Invalid password for user: {user_login.username}")
                return None

            # Create session
            session = Session(
                username=user.username,
                created_at=datetime.now(),
                expires_at=datetime.now() + self.session_duration
            )

            # Store session
            self.sessions[session.session_id] = session

            # Update last login time
            user.last_login = datetime.now()
            await self.storage.save_user(user)

            logger.info(f"User logged in successfully: {user.username}")
            return session

        except Exception as e:
            logger.error(f"Error during login: {e}")
            return None

    def logout(self, session_id: str) -> bool:
        """
        Logout user and destroy session

        Args:
            session_id: Session ID to destroy

        Returns:
            True if logout successful
        """
        if session_id in self.sessions:
            username = self.sessions[session_id].username
            del self.sessions[session_id]
            logger.info(f"User logged out: {username}")
            return True
        return False

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID

        Args:
            session_id: Session ID

        Returns:
            Session object if valid, None otherwise
        """
        session = self.sessions.get(session_id)

        if session is None:
            return None

        # Check if expired
        if session.is_expired():
            del self.sessions[session_id]
            logger.info(f"Session expired: {session.username}")
            return None

        return session

    def validate_session(self, session_id: str) -> Optional[str]:
        """
        Validate session and return username

        Args:
            session_id: Session ID to validate

        Returns:
            Username if session is valid, None otherwise
        """
        session = self.get_session(session_id)
        return session.username if session else None

    async def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """
        Change user password

        Args:
            username: Username
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully
        """
        try:
            # Get user
            user = await self.storage.get_user(username.lower())
            if not user:
                return False

            # Verify old password
            if not self.verify_password(old_password, user.password_hash):
                logger.warning(f"Invalid old password for user: {username}")
                return False

            # Hash new password
            user.password_hash = self.hash_password(new_password)

            # Save updated user
            success = await self.storage.save_user(user)
            if success:
                logger.info(f"Password changed successfully for user: {username}")
            return success

        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return False

    async def update_user_profile(self, username: str, updates: Dict) -> bool:
        """
        Update user profile information

        Args:
            username: Username
            updates: Dictionary of fields to update

        Returns:
            True if update successful
        """
        try:
            # Get user
            user = await self.storage.get_user(username.lower())
            if not user:
                return False

            # Update allowed fields
            allowed_fields = ['email', 'full_name', 'pushover_key', 'telegram_chat_id', 'timezone']
            for field, value in updates.items():
                if field in allowed_fields and hasattr(user, field):
                    setattr(user, field, value)

            # Save updated user
            success = await self.storage.save_user(user)
            if success:
                logger.info(f"Profile updated for user: {username}")
            return success

        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False

    def cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        expired = [sid for sid, session in self.sessions.items() if session.is_expired()]
        for sid in expired:
            username = self.sessions[sid].username
            del self.sessions[sid]
            logger.info(f"Cleaned up expired session for user: {username}")
        return len(expired)
