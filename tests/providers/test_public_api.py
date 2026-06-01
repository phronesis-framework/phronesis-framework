"""Smoke tests for the public API of :mod:`phronesis.providers`."""

from __future__ import annotations

import phronesis.providers as providers_pkg
from phronesis.providers.anthropic.factory import anthropic as _anthropic_impl
from phronesis.providers.chunks import Finish as _FinishImpl
from phronesis.providers.chunks import LLMChunk as _LLMChunkImpl
from phronesis.providers.chunks import TextChunk as _TextChunkImpl
from phronesis.providers.chunks import ToolCallEnd as _ToolCallEndImpl
from phronesis.providers.chunks import ToolCallStart as _ToolCallStartImpl
from phronesis.providers.chunks import ToolResult as _ToolResultImpl
from phronesis.providers.errors import AuthenticationError as _AuthImpl
from phronesis.providers.errors import BadRequestError as _BadReqImpl
from phronesis.providers.errors import ContextWindowExceededError as _CtxImpl
from phronesis.providers.errors import ProviderError as _ProviderErrImpl
from phronesis.providers.errors import RateLimitError as _RateImpl
from phronesis.providers.errors import ServerError as _ServerImpl
from phronesis.providers.errors import StreamError as _StreamImpl
from phronesis.providers.errors import TransportError as _TransportImpl
from phronesis.providers.openai.factory import openai as _openai_impl
from phronesis.providers.protocol import LLMProvider as _LLMProviderImpl
from phronesis.providers.protocol import ProviderFeature as _ProviderFeatureImpl
from phronesis.providers.retry_config import RetryConfig as _RetryConfigImpl
from phronesis.providers.types import LLMRequest as _LLMRequestImpl
from phronesis.providers.types import LLMResponse as _LLMResponseImpl
from phronesis.providers.types import MediaRef as _MediaRefImpl
from phronesis.providers.types import Message as _MessageImpl
from phronesis.providers.types import ResponseFormat as _ResponseFormatImpl
from phronesis.providers.types import Role as _RoleImpl
from phronesis.providers.types import ToolCall as _ToolCallImpl
from phronesis.providers.usage import TokenUsage as _TokenUsageImpl

_EXPECTED_NAMES = {
    "AuthenticationError": _AuthImpl,
    "BadRequestError": _BadReqImpl,
    "ContextWindowExceededError": _CtxImpl,
    "Finish": _FinishImpl,
    "LLMChunk": _LLMChunkImpl,
    "LLMProvider": _LLMProviderImpl,
    "LLMRequest": _LLMRequestImpl,
    "LLMResponse": _LLMResponseImpl,
    "MediaRef": _MediaRefImpl,
    "Message": _MessageImpl,
    "ProviderError": _ProviderErrImpl,
    "ProviderFeature": _ProviderFeatureImpl,
    "RateLimitError": _RateImpl,
    "ResponseFormat": _ResponseFormatImpl,
    "RetryConfig": _RetryConfigImpl,
    "Role": _RoleImpl,
    "ServerError": _ServerImpl,
    "StreamError": _StreamImpl,
    "TextChunk": _TextChunkImpl,
    "TokenUsage": _TokenUsageImpl,
    "ToolCall": _ToolCallImpl,
    "ToolCallEnd": _ToolCallEndImpl,
    "ToolCallStart": _ToolCallStartImpl,
    "ToolResult": _ToolResultImpl,
    "TransportError": _TransportImpl,
    "anthropic": _anthropic_impl,
    "openai": _openai_impl,
}


class TestProvidersPackageAll:
    def test_all_is_sorted_and_unique(self) -> None:
        names = list(providers_pkg.__all__)

        assert names == sorted(names)
        assert len(names) == len(set(names))

    def test_all_matches_expected_set(self) -> None:
        assert set(providers_pkg.__all__) == set(_EXPECTED_NAMES)

    def test_every_name_is_importable_from_package(self) -> None:
        for name, expected in _EXPECTED_NAMES.items():
            assert getattr(providers_pkg, name) is expected


class TestErrorHierarchy:
    def test_all_concrete_errors_inherit_from_provider_error(self) -> None:
        concrete = (
            _AuthImpl,
            _BadReqImpl,
            _CtxImpl,
            _RateImpl,
            _ServerImpl,
            _StreamImpl,
            _TransportImpl,
        )

        for cls in concrete:
            assert issubclass(cls, _ProviderErrImpl)


class TestFactoryWiring:
    def test_anthropic_factory_is_re_exported(self) -> None:
        assert providers_pkg.anthropic is _anthropic_impl

    def test_openai_factory_is_re_exported(self) -> None:
        assert providers_pkg.openai is _openai_impl
