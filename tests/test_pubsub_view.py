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


class DjangoTasksPubSubPushViewTests(SimpleTestCase):
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
    def test_BLAHBLAH(self, mocked_dispatch):
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
    
    # Test malformed pubsub message json data should return 400 and 
    # log error
    def test_malformed_pubsub_message_json_data_returns_400(self):
        request = self.request_factory.post(
            "/pubsub/",
            data="invalid json",
            content_type="application/json",
        )

        response = PubSubPushView.as_view()(request)

        self.assertEqual(response.status_code, 400)

        # log error
        with self.assertLogs("django_tasks_pubsub.views", level="ERROR") as cm:
            PubSubPushView.as_view()(request)
            self.assertIn(
                'ERROR:django_tasks_pubsub.views:PubSubPushView: invalid JSON body',
                cm.output
            )

    # Test pubsub message missing data should return 400 and log error
    def test_pubsub_message_missing_data_returns_400(self):
        request = self.request_factory.post(
            "/pubsub/",
            data=json.dumps({"message": {}}),
            content_type="application/json",
        )

        response = PubSubPushView.as_view()(request)

        self.assertEqual(response.status_code, 400)

        # log error
        with self.assertLogs("django_tasks_pubsub.views", level="ERROR") as cm:
            PubSubPushView.as_view()(request)
            self.assertIn(
                'ERROR:django_tasks_pubsub.views:PubSubPushView: missing message.data',
                cm.output
            )
    
    # Test if data is empty string should return 400 and log error
    def test_empty_data_returns_400(self):
        request = self.request_factory.post(
            "/pubsub/",
            data=json.dumps({"message": {"data": ""}}),
            content_type="application/json",
        )

        response = PubSubPushView.as_view()(request)

        self.assertEqual(response.status_code, 400)

        # log error
        with self.assertLogs("django_tasks_pubsub.views", level="ERROR") as cm:
            PubSubPushView.as_view()(request)
            self.assertIn(
                'ERROR:django_tasks_pubsub.views:PubSubPushView: empty message.data',
                cm.output
            )

    # Test no existant function to execute returns 500 and log error
    def test_no_existant_function_to_execute_returns_500(self):
        request = self.request_factory.post(
            "/pubsub/",
            data=json.dumps(
                {
                    "message": {
                        "data": base64.b64encode(
                            json.dumps(
                                {
                                    "task": {
                                        "backend": "default",
                                        "module_path": "tests.test_pubsub_view", 
                                        "name": "non_existant_function",
                                        "priority": 0,
                                        "queue_name": "default",
                                        "takes_context": False
                                    },
                                    "task_id": "test-task-id",
                                    "enqueued_at": "2026-05-12T10:00:00+00:00",
                                    "args": [],
                                    "kwargs": {}
                                }
                            ).encode("utf-8")
                        ).decode("utf-8")
                    }
                }
            ),
            content_type="application/json",
        )

        with self.subTest("Should have 500 since function does not exist"):
            response = PubSubPushView.as_view()(request)
            self.assertEqual(response.status_code, 500)

        # log error
        with self.assertLogs("django_tasks_pubsub.views", level="ERROR") as cm:
            PubSubPushView.as_view()(request)
            found_errors = []
            for line in cm.output:
                if line.startswith("ERROR:django_tasks_pubsub.views:PubSubPushView: task failed"):
                    found_errors.append(line)

            self.assertEqual(len(found_errors), 1)
    
    # Test payload data with missing attribues in the task payload
    # so it fails to create a task object, should return 400 and log error
    def test_payload_data_with_missing_attributes_in_the_task_payload_returns_400(self):
        request = self.request_factory.post(
            "/pubsub/",
            data=json.dumps(
                {
                    "message": {
                        "data": base64.b64encode(
                            json.dumps(
                                {
                                    "task": {
                                        "backend": "default",
                                        "module_path": "tests.test_pubsub_view", 
                                        "name": "sample_task_function",
                                        "priority": 0,
                                        "queue_name": "default",
                                        "takes_context": False
                                    },
                                    "task_id": "test-task-id",
                                    "enqueued_at": "2026-05-12T10:00:00+00:00",
                                    # Missing args and kwargs
                                }
                            ).encode("utf-8")
                        ).decode("utf-8")
                    }
                }
            ),
            content_type="application/json",
        )

        response = PubSubPushView.as_view()(request)

        with self.subTest("Should have 400 since task object is missing attributes"): 
            self.assertEqual(response.status_code, 400)
        
        with self.assertLogs("django_tasks_pubsub.views", level="ERROR") as cm:
            PubSubPushView.as_view()(request)
            found_errors = []
            for line in cm.output:
                if line.startswith("ERROR:django_tasks_pubsub.views:PubSubPushView: failed to instantiate payload object from data"):
                    found_errors.append(line)

            self.assertEqual(len(found_errors), 1)

    # Test payload data that is not valid json, should return 400 and log error
    def test_payload_data_that_is_not_valid_json_returns_400(self):
        request = self.request_factory.post(
            "/pubsub/",
            data=json.dumps(
                {
                    "message": {
                        "data": base64.b64encode(
                            bytes("invalid json", "utf-8")
                        ).decode("utf-8")
                    }
                }
            ),
            content_type="application/json",
        )

        response = PubSubPushView.as_view()(request)

        with self.subTest("Should have 400 since base64 decoded data is not valid json"): 
            self.assertEqual(response.status_code, 400)
        
        with self.assertLogs("django_tasks_pubsub.views", level="ERROR") as cm:
            PubSubPushView.as_view()(request)
            found_errors = []
            for line in cm.output:
                if line.startswith("ERROR:django_tasks_pubsub.views:PubSubPushView: failed to parse json payload"):
                    found_errors.append(line)

            self.assertEqual(len(found_errors), 1, cm.output)

    # Test payload data that is not valid base64, should return 400 and log error
    def test_payload_data_that_is_not_valid_base64_returns_400(self):
        request = self.request_factory.post(
            "/pubsub/",
            data=json.dumps(
                {
                    "message": {
                        "data": "invalid base64"
                    }
                }
            ),
            content_type="application/json",
        )

        response = PubSubPushView.as_view()(request)

        with self.subTest("Should have 400 since base64 data is not valid"):
            self.assertEqual(response.status_code, 400)

        with self.assertLogs("django_tasks_pubsub.views", level="ERROR") as cm:
            PubSubPushView.as_view()(request)
            found_errors = []
            for line in cm.output:
                if line.startswith("ERROR:django_tasks_pubsub.views:PubSubPushView: failed to decode base64 data"):
                    found_errors.append(line)

            self.assertEqual(len(found_errors), 1, cm.output)