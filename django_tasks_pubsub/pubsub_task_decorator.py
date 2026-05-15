from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class PubSubMetaData:
    topic_id: str | None = None


def pubsub_task(topic_id: str | None = None):
    def wrapper(func: Callable):
        setattr(
            func,
            "__pubsub_metadata",
            PubSubMetaData(topic_id=topic_id),
        )
        return func

    return wrapper
