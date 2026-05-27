from typing import Optional


class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email


class UserService:
    """User management service."""

    def get_user(self, user_id: int) -> User:
        """Returns the User for the given ID."""
        pass

    def create_user(self, name: str, email: str) -> User:
        """Creates and returns a new User."""
        pass

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Finds a user by email address. Returns None if not found."""
        pass

    def _internal_cache_reset(self) -> None:
        """Private cache management — not part of public API."""
        pass
