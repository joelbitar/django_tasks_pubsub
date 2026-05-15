import importlib
from datetime import datetime

from django.tasks import TaskContext
from django.tasks.base import TaskResultStatus

from django_tasks_pubsub.backend import Payload, TaskResult


def dispatch(payload: Payload):
    module_path = payload.task.module_path
    task_name = payload.task.name

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError:
        module_path, task_name_from_path = module_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        task_name = task_name or task_name_from_path

    # This is the decorated task function, decoration makes it a Task object
    task = getattr(module, task_name)

    # Actual task function that we can call
    task_function = getattr(task, "func", task)

    if payload.task.takes_context:
        context = TaskContext(
            task_result=TaskResult(
                id=payload.task_id,
                task=task,
                enqueued_at=datetime.fromisoformat(payload.enqueued_at),
                started_at=None,
                finished_at=None,
                status=TaskResultStatus.READY,
                args=payload.args,
                kwargs=payload.kwargs,
                last_attempted_at=None,
                backend=payload.task.backend,
                errors=[],
                worker_ids=[],
            ),
        )
        task_function(
            context,
            *payload.args,
            **payload.kwargs,
        )
        return

    task_function(
        *payload.args,
        **payload.kwargs,
    )
