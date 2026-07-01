from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models import PlatformEvent
from app.models.entities import now_utc
from app.schemas.serializers import platform_event_to_dict

_run_queues: dict[int, set[asyncio.Queue]] = defaultdict(set)


def record_event(
    db: Session,
    *,
    category: str,
    message: str,
    level: str = "info",
    run_id: int | None = None,
    device_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> PlatformEvent:
    event = PlatformEvent(
        run_id=run_id,
        device_id=device_id,
        level=level,
        category=category,
        message=message,
        payload=payload or {},
        created_at=now_utc(),
    )
    db.add(event)
    db.flush()
    publish_event(event)
    return event


def publish_event(event: PlatformEvent) -> None:
    if event.run_id is None:
        return
    payload = platform_event_to_dict(event)
    queues = list(_run_queues.get(event.run_id, set()))
    for queue in queues:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass


def subscribe_run(run_id: int) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _run_queues[run_id].add(queue)
    return queue


def unsubscribe_run(run_id: int, queue: asyncio.Queue) -> None:
    queues = _run_queues.get(run_id)
    if not queues:
        return
    queues.discard(queue)
    if not queues:
        _run_queues.pop(run_id, None)
