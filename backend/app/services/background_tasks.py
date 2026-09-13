"""Minimal background-job abstraction (spec §14): "If Redis/Celery is already available, reuse it.
Otherwise create an interface allowing local development execution without blocking production
architecture." Neither Redis nor Celery is wired up anywhere in this codebase yet (see
ARCHITECTURE.md's `workers/` — APScheduler/Celery, not yet implemented), so this is the interface a
future Celery/RQ-backed runner would implement, with `InlineTaskRunner` as the only implementation
that exists today: the webhook endpoints still go through `enqueue()`, they just get their work
done synchronously underneath it. Swapping to a real queue later means writing one new class here,
not touching a single webhook route.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable


class BackgroundTaskRunner(ABC):
    @abstractmethod
    async def enqueue(self, task_name: str, handler: Callable[[], Awaitable[None]]) -> None: ...


class InlineTaskRunner(BackgroundTaskRunner):
    async def enqueue(self, task_name: str, handler: Callable[[], Awaitable[None]]) -> None:
        await handler()
