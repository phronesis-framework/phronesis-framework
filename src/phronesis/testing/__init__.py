"""Public testing helpers for users of Phronesis.

The :mod:`phronesis.testing` module exposes utilities that are useful
when writing unit tests against agent code without touching real LLM
providers. Two providers are exported:

* :class:`FakeProvider` — always returns the same canned response.
* :class:`ScriptedProvider` — pops responses from a queue, one per
  ``complete`` call.

These helpers are deliberately minimal; they implement the
:class:`phronesis.providers.protocol.LLMProvider` Protocol but do not
attempt to simulate streaming, tool-call dispatch or rate limits.
"""

from __future__ import annotations

from phronesis.testing.providers import FakeProvider as FakeProvider
from phronesis.testing.providers import ScriptedProvider as ScriptedProvider
