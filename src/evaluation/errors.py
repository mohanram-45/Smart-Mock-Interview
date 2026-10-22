"""Provider error taxonomy. `retryable` drives the bounded retry loop; nothing is retried that cannot succeed on retry."""


class ProviderError(Exception):
    code = "provider_error"
    retryable = False

    def __init__(self, message: str = "", *, retry_after: float | None = None):
        super().__init__(message or self.code)
        self.retry_after = retry_after


class ProviderNotConfigured(ProviderError):
    code = "provider_not_configured"


class ProviderAuthError(ProviderError):
    code = "provider_auth_error"          # 401/403: retrying cannot help


class ProviderRequestError(ProviderError):
    code = "provider_request_error"       # other 4xx: our request is wrong


class ProviderTimeout(ProviderError):
    code = "provider_timeout"
    retryable = True


class ProviderRateLimited(ProviderError):
    code = "provider_rate_limited"
    retryable = True


class ProviderUnavailable(ProviderError):
    code = "provider_unavailable"         # connection refused, DNS, 5xx
    retryable = True


class ProviderResponseError(ProviderError):
    code = "provider_bad_envelope"        # reachable, but the HTTP body is not the documented envelope
    retryable = False
