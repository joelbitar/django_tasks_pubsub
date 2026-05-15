from unittest.mock import patch, Mock

from django.tasks import task, TaskContext, Task
from django.test import SimpleTestCase
from django.test.utils import override_settings

from django_tasks_pubsub.dispatcher import dispatch
from django_tasks_pubsub.backend import Payload, TaskPayload

sample_task_with_context_mock = Mock()


@task(takes_context=True)
def sample_task_with_context(context: TaskContext, specified_arg, *args, **kwargs):
    sample_task_with_context_mock(
        context,
        specified_arg,
        *args,
        **kwargs,
    )


@override_settings(PUBSUB_PROJECT_ID="project_name")
@override_settings(PUBSUB_DEFAULT_TOPIC_ID="default_topic_id")
@override_settings(TASKS={"default": {"BACKEND": "django_tasks_pubsub.PubSubBackend"}})
class TestPubSubBackendEnqueuing(SimpleTestCase):
    def setUp(self):
        self.get_topic_path_patcher = patch(
            "django_tasks_pubsub.google_cloud_pubsub_backend.GoogleCloudPubSubBackend.get_topic_path",
            return_value="expected/topic/path",
        )
        self.get_topic_path_mock = self.get_topic_path_patcher.start()

    def tearDown(self):
        self.get_topic_path_patcher.stop()


class TestPubSubTaskDispatching(SimpleTestCase):
    def setUp(self):
        sample_task_with_context_mock.reset_mock()

    def test_dispatching_task_with_context_passes_expected_context_to_task_function(
        self,
    ):
        payload = Payload(
            task=TaskPayload(
                backend="default",
                module_path="tests.test_dispatching_with_pubsub_task_backend",
                name="sample_task_with_context",
                priority=0,
                queue_name="default",
                takes_context=True,
            ),
            task_id="test-task-id",
            enqueued_at="2026-05-12T10:00:00+00:00",
            args=[
                "spec_arg",
                "arg1",
                "arg2",
            ],
            kwargs={
                "kwarg1": "val1",
                "kwarg2": "val2",
            },
        )

        dispatch(payload)

        sample_task_with_context_mock.assert_called_once()

        context: TaskContext = sample_task_with_context_mock.call_args.args[0]

        self.assertIsNotNone(context)

        with self.subTest("context contains the task result id"):
            self.assertEqual(context.task_result.id, "test-task-id")

        with self.subTest("task receives expected args and kwargs after context"):
            sample_task_with_context_mock.assert_called_once_with(
                context,
                "spec_arg",
                "arg1",
                "arg2",
                kwarg1="val1",
                kwarg2="val2",
            )

        # SubTest
        with self.subTest("context should be TaskContext"):
            self.assertIsInstance(context, TaskContext)

        called_task_result_task: Task = context.task_result.task

        self.assertIsNotNone(
            called_task_result_task,
        )

        self.assertIsInstance(
            called_task_result_task,
            Task,
        )

        # SubTest should have ALL the expected properties set
        with self.subTest(
            "should have ALL the expected properties set at the task oject"
        ):
            self.assertEqual(called_task_result_task.name, "sample_task_with_context")
            self.assertEqual(called_task_result_task.backend, "default")
            self.assertEqual(
                called_task_result_task.module_path,
                "tests.test_dispatching_with_pubsub_task_backend.sample_task_with_context",
            )
            self.assertEqual(called_task_result_task.priority, 0)
            self.assertEqual(called_task_result_task.queue_name, "default")
            self.assertEqual(called_task_result_task.takes_context, True)
            self.assertEqual(
                called_task_result_task.func,
                sample_task_with_context.func,
            )
