class AuthError(Exception):
    """Base authentication error."""

    pass


class UserAlreadyExistsError(AuthError):
    """Raised when trying to register with an existing email."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"User with email {email} already exists")


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class InvalidTokenError(AuthError):
    """Raised when token is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired token") -> None:
        super().__init__(message)


class UserNotApprovedError(AuthError):
    """Raised when user account is not yet approved by admin."""

    def __init__(self) -> None:
        super().__init__("Your account is pending approval by an administrator")


class InsufficientPermissionsError(AuthError):
    """Raised when user doesn't have required permissions."""

    def __init__(self, message: str = "You don't have permission to perform this action") -> None:
        super().__init__(message)
