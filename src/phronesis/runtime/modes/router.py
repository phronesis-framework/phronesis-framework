"""Router: dispatch to a named route based on a classifier."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import NoMatchingRouteError
from phronesis.runtime.obs import RUNTIME_ROUTE, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Router:
    """Dispatch to a route based on a classifier.

    Attributes:
        classifier: Sync or async callable returning the route key.
        routes: Mapping of route key to executable.
        default: Optional fallback executable when no route matches.
    """

    classifier: Callable[[Any], Awaitable[str] | str]
    routes: Mapping[str, Executable]
    default: Executable | None = None

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        route = self.classifier(input)

        if inspect.isawaitable(route):
            route = await route

        async with runtime_span(
            "router",
            run_id=ctx.run_id.canonical,
            extra={RUNTIME_ROUTE: route},
        ):
            node = self.routes.get(route)

            if node is None:
                node = self.default

                if node is None:
                    return RunOutcome.fail(
                        error=NoMatchingRouteError(
                            f"no matching route for key {route!r}",
                            details={"route": route},
                        )
                    )

            outcome = await node(ctx.child(metadata={RUNTIME_ROUTE: route}), input)

            return outcome
