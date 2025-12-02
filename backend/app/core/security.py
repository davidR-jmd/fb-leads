from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.core.interfaces import IPasswordHasher, ITokenService

settings = get_settings()


class PasswordHasher(IPasswordHasher):
    """Bcrypt password hasher implementation (Single Responsibility)."""

    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


class JWTService(ITokenService):
    """JWT token service implementation (Single Responsibility)."""

    def __init__(
        self,
        secret_key: str = settings.jwt_secret_key,
        algorithm: str = settings.jwt_algorithm,
        access_expire_minutes: int = settings.jwt_access_token_expire_minutes,
        refresh_expire_days: int = settings.jwt_refresh_token_expire_days,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_expire_minutes = access_expire_minutes
        self._refresh_expire_days = refresh_expire_days

    def create_access_token(self, data: dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(minutes=self._access_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, data: dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self._refresh_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict[str, Any] | None:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return payload
        except JWTError:
            return None


# Default instances (can be overridden for testing via Dependency Injection)
password_hasher = PasswordHasher()
jwt_service = JWTService()
