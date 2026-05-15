import base64
import json
from unittest.mock import patch, Mock

from django.tasks import task
from django.test import RequestFactory, SimpleTestCase

from django_tasks_pubsub.backend import Payload, TaskPayload
from django_tasks_pubsub.views import PubSubPushView

sample_task_function_mock = Mock()


@task
def sample_task_function(specified_arg, *args, **kwargs):
    sample_task_function_mock(specified_arg, *args, **kwargs)


class TestDjangoTasksPubSubPushView(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def build_pubsub_push_request(self, payload: dict):
        encoded_payload = base64.b64encode(
            json.dumps(payload).encode("utf-8"),
        ).decode("utf-8")

        envelope = {
            "message": {
                "data": encoded_payload,
                "messageId": "test-message-id",
                "publishTime": "2026-05-12T10:00:00Z",
            },
            "subscription": "projects/test-project/subscriptions/test-subscription",
        }

        return self.request_factory.post(
            "/pubsub/",
            data=json.dumps(envelope),
            content_type="application/json",
        )

    @patch("django_tasks_pubsub.views.dispatch")
    def test_pubsub_view_calls_dispatch_with_expected_payload(self, mocked_dispatch):
        payload = {
            "task": {
                "backend": "default",
                "module_path": "django_tasks_pubsub.tests.test_pubsub_view",
                "name": "sample_task",
                "priority": 0,
                "queue_name": "default",
                "takes_context": False,
            },
            "task_id": "test-task-id",
            "enqueued_at": "2026-05-12T10:00:00+00:00",
            "args": [
                "spec_arg",
                "arg1",
                "arg2",
            ],
            "kwargs": {
                "kwarg1": "val1",
                "kwarg2": "val2",
            },
        }

        request = self.build_pubsub_push_request(payload)

        response = PubSubPushView.as_view()(request)

        self.assertEqual(response.status_code, 204)

        with self.subTest("dispatch is called once"):
            mocked_dispatch.assert_called_once()

        with self.subTest("dispatch is called with payload object"):
            mocked_dispatch.assert_called_once_with(
                payload=Payload(
                    task=TaskPayload(**payload.pop("task")),
                    **payload,
                )
            )

    def test_pubsub_view_calls_actual_task_function_with_expected_arguments(self):
        payload = {
            "task": {
                "backend": "default",
                "module_path": "tests.test_pubsub_view",
                "name": "sample_task_function",
                "priority": 0,
                "queue_name": "default",
                "takes_context": False,
            },
            "task_id": "test-task-id",
            "enqueued_at": "2026-05-12T10:00:00+00:00",
            "args": [
                "spec_arg",
                "arg1",
                "arg2",
            ],
            "kwargs": {
                "kwarg1": "val1",
                "kwarg2": "val2",
            },
        }

        request = self.build_pubsub_push_request(payload)

        response = PubSubPushView.as_view()(request)

        self.assertEqual(response.status_code, 204)

        with self.subTest("actual task function is called with expected arguments"):
            sample_task_function_mock.assert_called_once_with(
                "spec_arg",
                "arg1",
                "arg2",
                kwarg1="val1",
                kwarg2="val2",
            )
