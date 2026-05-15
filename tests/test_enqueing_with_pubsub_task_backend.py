import json
from datetime import datetime
from unittest.mock import patch, Mock

from django.tasks import task
from django.test import SimpleTestCase
from django.test.utils import override_settings

from django_tasks_pubsub import pubsub_task


@task
def sample_task(specified_arg, *args, **kwargs):
    pass


@task(takes_context=True)
def sample_task_with_context(context, specified_arg, *args, **kwargs):
    pass


@task
@pubsub_task("test-topic-name")
def sample_task_with_pubsub_topic(specified_arg, *args, **kwargs):
    pass


sample_task_with_pubsub_topic_watchdog = Mock()


@task
@pubsub_task("test-topic-name")
def sample_task_with_pubsub_topic_with_watchdog(*args, **kwargs):
    sample_task_with_pubsub_topic_watchdog(
        *args,
        **kwargs,
    )


@override_settings(PUBSUB_PROJECT_ID="project_name")
@override_settings(PUBSUB_DEFAULT_TOPIC_ID="default_topic_id")
@override_settings(TASKS={"default": {"BACKEND": "django_tasks_pubsub.PubSubBackend"}})
class TestPubsubTopicGeneration(SimpleTestCase):
    @override_settings(PUBSUB_DEFAULT_TOPIC_ID="other_default_topic_id")
    @patch("django_tasks_pubsub.backend.get_publisher")
    @patch("django_tasks_pubsub.backend.publish", return_value="")
    def test_enqueuing_a_task_with_out_topic_defined_should_use_default(
        self, mocked_publish_method, mocked_get_publisher
    ):
        class DummyPublisher:
            def __init__(self):
                self.topic_path = Mock()

        dummy_publisher = DummyPublisher()

        mocked_get_publisher.return_value = dummy_publisher

        sample_task.enqueue(
            "spec_arg",
            "arg1",
        )

        dummy_publisher.topic_path.assert_called_once_with(
            "project_name",
            "other_default_topic_id",
        )

    @patch("django_tasks_pubsub.backend.get_publisher")
    @patch("django_tasks_pubsub.backend.publish", return_value="")
    def test_enqueuing_a_task_with_pubsub_topic(
        self, mocked_publish_method, mocked_get_publisher
    ):
        class DummyPublisher:
            def __init__(self):
                self.topic_path = Mock()

        dummy_publisher = DummyPublisher()

        mocked_get_publisher.return_value = dummy_publisher

        sample_task_with_pubsub_topic.enqueue(
            "spec_arg",
            "arg1",
        )

        dummy_publisher.topic_path.assert_called_once_with(
            "project_name",
            "test-topic-name",
        )

    @patch("django_tasks_pubsub.backend.publish", return_value="")
    @patch(
        "django_tasks_pubsub.PubSubBackend.get_topic_path",
        return_value="expected/topic/path",
    )
    def test_enqueuing_task_should_use_value_from_get_topic_path(
        self, mocked_get_topic_path, mocked_publish_method
    ):
        sample_task.enqueue(
            "spec_arg",
            "arg1",
            "arg2",
        )

        self.assertEqual(mocked_publish_method.call_count, 1)
        self.assertEqual(
            mocked_publish_method.call_args.kwargs["topic"],
            "expected/topic/path",
        )


@override_settings(TASKS={"default": {"BACKEND": "django_tasks_pubsub.PubSubBackend"}})
class TestPubSubBackendEnqueuing(SimpleTestCase):
    def setUp(self):
        self.get_topic_path_patcher = patch(
            "django_tasks_pubsub.backend.PubSubBackend.get_topic_path",
            return_value="expected/topic/path",
        )
        self.get_topic_path_mock = self.get_topic_path_patcher.start()

    def tearDown(self):
        self.get_topic_path_patcher.stop()

    @patch("django_tasks_pubsub.backend.publish", return_value="")
    def test_enqueuing_a_task_with_the_pub_sub_backend_should_not_raise_an_error(
        self, mocked_publish_method
    ):
        sample_task.enqueue(
            "spec_arg",
            "arg1",
            "arg2",
            kwarg1="val1",
            kwarg2="val2",
        )

        self.assertEqual(mocked_publish_method.call_count, 1)

        with self.subTest("payload data is serialized as expected"):
            payload_data = mocked_publish_method.call_args.kwargs["data"]
            payload = json.loads(payload_data.decode("utf-8"))

            self.assertIn("task", payload)
            self.assertIn("task_id", payload)
            self.assertIn("enqueued_at", payload)
            self.assertIn("args", payload)
            self.assertIn("kwargs", payload)

            datetime.fromisoformat(payload["enqueued_at"])

            self.assertEqual(
                payload["args"],
                ["spec_arg", "arg1", "arg2"],
            )
            self.assertEqual(
                payload["kwargs"],
                {
                    "kwarg1": "val1",
                    "kwarg2": "val2",
                },
            )

            self.assertEqual(payload["task"]["name"], "sample_task")
            self.assertEqual(payload["task"]["takes_context"], False)
            self.assertEqual(
                payload["task"]["module_path"],
                "tests.test_enqueing_with_pubsub_task_backend.sample_task",
            )
            self.assertEqual(
                payload["task"]["name"],
                "sample_task",
            )

            self.assertIsNone(
                payload["task"]["run_after"],
            )

    @patch("django_tasks_pubsub.backend.publish", return_value="")
    def test_enqueuing_a_task_with_context_with_the_pub_sub_backend_should_not_raise_an_error(
        self, mocked_publish_method
    ):
        sample_task_with_context.enqueue(
            "spec_arg",
            "arg1",
            "arg2",
            kwarg1="val1",
            kwarg2="val2",
        )

        self.assertEqual(mocked_publish_method.call_count, 1)


class TestPubSubTopicEnqueuingWithImmediateBackend(SimpleTestCase):
    @override_settings(
        TASKS={
            "default": {"BACKEND": "django.tasks.backends.immediate.ImmediateBackend"}
        }
    )
    def test_enqueuing_a_task_with_pubsub_topic_should_raise_an_error(self):
        sample_task_with_pubsub_topic_with_watchdog.enqueue(
            "arg1",
            "arg2",
        )

        self.assertEqual(sample_task_with_pubsub_topic_watchdog.call_count, 1)

        self.assertEqual(
            sample_task_with_pubsub_topic_watchdog.call_args.args[0], "arg1"
        )
        self.assertEqual(
            sample_task_with_pubsub_topic_watchdog.call_args.args[1], "arg2"
        )
