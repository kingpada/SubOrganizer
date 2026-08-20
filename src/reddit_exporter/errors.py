class AppError(Exception):
    """Base application error."""


class ConfigurationError(AppError):
    pass


class CredentialStoreError(AppError):
    pass


class AuthenticationError(AppError):
    pass


class OAuthStateMismatch(AuthenticationError):
    pass


class AuthorizationDenied(AuthenticationError):
    pass


class InsufficientScopeError(AuthenticationError):
    pass


class RateLimitError(AppError):
    pass


class RedditApiError(AppError):
    pass


class NetworkError(AppError):
    pass


class ExportError(AppError):
    pass
