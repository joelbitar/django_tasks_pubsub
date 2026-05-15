import dataclasses
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.tasks import Task
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.base import TaskResult as BaseTaskResult, TaskResultStatus
from django.utils import timezone
from django.utils.crypto import get_random_string

from django_tasks_pubsub.publisher import get_publisher
from django_tasks_pubsub.publisher import publish
from django_tasks_pubsub.pubsub_task_decorator import PubSubMetaData


@dataclass(frozen=True)
class TaskPayload:
    backend: str
    module_path: str
    name: str
    priority: int
    queue_name: str
    takes_context: bool
    run_after: Optional[datetime] = None


@dataclass(frozen=True)
class Payload:
    task: TaskPayload
    task_id: str
    enqueued_at: str
    args: list
    kwargs: dict


class TaskResult(BaseTaskResult):
    pass


class PubSubBackend(BaseTaskBackend):
    @staticmethod
    def get_pubsub_metadata(task: Task) -> PubSubMetaData:
        task_func = getattr(task, "func")

        return getattr(task_func, "__pubsub_metadata", PubSubMetaData())

    def get_topic_id(self, task: Task):
        return (
            self.get_pubsub_metadata(task=task).topic_id
            or settings.PUBSUB_DEFAULT_TOPIC_ID
        )

    def get_topic_path(self, task: Task):
        topic_id = self.get_topic_id(task)

        publisher = get_publisher()

        topic_path = publisher.topic_path(
            settings.PUBSUB_PROJECT_ID,
            topic_id,
        )

        return topic_path

    def enqueue(self, task: Task, args, kwargs):
        enqueued_at = timezone.now()
        task_id = get_random_string(32)

        payload: Payload = Payload(
            task=TaskPayload(
                backend=task.backend,
                module_path=task.module_path,
                name=task.name,
                priority=task.priority,
                queue_name=task.queue_name,
                takes_context=task.takes_context,
            ),
            task_id=task_id,
            enqueued_at=enqueued_at.isoformat(),
            args=args,
            kwargs=kwargs,
        )
        # Data to send to the queue.
        data = json.dumps(
            dataclasses.asdict(payload),
        ).encode("utf-8")

        topic_path = self.get_topic_path(
            task,
        )

        publish(topic=topic_path, data=data)

        return TaskResult(
            id=task_id,
            task=task,
            enqueued_at=enqueued_at,
            started_at=None,
            finished_at=None,
            status=TaskResultStatus.READY,
            args=args,
            kwargs=kwargs,
            last_attempted_at=None,
            backend=task.backend,
            errors=[],
            worker_ids=[],
        )
