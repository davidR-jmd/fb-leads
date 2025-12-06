"""LinkedIn module exceptions (Single Responsibility)."""


class LinkedInError(Exception):
    """Base exception for LinkedIn operations."""

    def __init__(self, message: str = "LinkedIn error occurred"):
        self.message = message
        super().__init__(self.message)


class LinkedInNotConfiguredError(LinkedInError):
    """Raised when LinkedIn is not configured."""

    def __init__(self):
        super().__init__("LinkedIn credentials not configured")


class LinkedInConnectionError(LinkedInError):
    """Raised when connection to LinkedIn fails."""

    def __init__(self, message: str = "Failed to connect to LinkedIn"):
        super().__init__(message)


class LinkedInAuthenticationError(LinkedInError):
    """Raised when LinkedIn authentication fails."""

    def __init__(self, message: str = "Invalid LinkedIn credentials"):
        super().__init__(message)


class LinkedInVerificationRequiredError(LinkedInError):
    """Raised when LinkedIn requires email/SMS verification."""

    def __init__(self, message: str = "Verification code required"):
        super().__init__(message)


class LinkedInBrowserBusyError(LinkedInError):
    """Raised when browser is busy with another operation."""

    def __init__(self):
        super().__init__("LinkedIn browser is busy, please try again later")


class LinkedInBrowserNotRunningError(LinkedInError):
    """Raised when browser is not running."""

    def __init__(self):
        super().__init__("LinkedIn browser is not running")


class LinkedInInvalidVerificationCodeError(LinkedInError):
    """Raised when verification code is invalid."""

    def __init__(self):
        super().__init__("Invalid verification code")
