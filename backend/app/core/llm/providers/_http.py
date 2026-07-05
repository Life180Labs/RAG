"""Shared HTTP error classification (docs/02-architecture.md section 86):
every provider's `generate()`/`stream()` funnels `httpx` failures through
this so the retry/fallback policy in `gateway.py` sees the same three
categories regardless of which provider raised them."""

import httpx

from app.core.llm.base import (
    InvalidRequestError,
    ProviderAuthError,
    TransientProviderError,
)


def raise_for_provider_status(response: httpx.Response, *, provider: str) -> None:
    if response.status_code < 400:
        return
    body_snippet = response.text[:500]
    if response.status_code in (401, 403):
        raise ProviderAuthError(
            f"{provider} rejected the request credentials ({response.status_code}): "
            f"{body_snippet}",
            provider=provider,
        )
    if response.status_code == 429 or response.status_code >= 500:
        raise TransientProviderError(
            f"{provider} returned a transient error ({response.status_code}): {body_snippet}",
            provider=provider,
        )
    raise InvalidRequestError(
        f"{provider} rejected the request ({response.status_code}): {body_snippet}",
        provider=provider,
    )


def wrap_transport_error(exc: Exception, *, provider: str) -> TransientProviderError:
    return TransientProviderError(
        f"{provider} request failed: {exc}", provider=provider
    )
