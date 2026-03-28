import httpx

_DEFAULT_RETRY_AFTER = 60  # seconds


class RateLimitError(Exception):
    """Raised when the API returns HTTP 429."""

    def __init__(self, retry_after: int = _DEFAULT_RETRY_AFTER) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limited; retry after {retry_after}s")


class NonRetryableHTTPError(Exception):
    """Raised for 4xx responses that must not be retried."""


def check_response(resp: httpx.Response) -> None:
    """Raise typed exceptions based on HTTP status."""
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", _DEFAULT_RETRY_AFTER))
        raise RateLimitError(retry_after)
    if 400 <= resp.status_code < 500:
        raise NonRetryableHTTPError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    resp.raise_for_status()  # propagates 5xx as httpx.HTTPStatusError
