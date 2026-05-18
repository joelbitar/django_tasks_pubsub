from unittest.mock import Mock

from django.test import SimpleTestCase

from django_tasks_pubsub.backend import Payload, TaskPayload
from django_tasks_pubsub.dispatcher import dispatch

dummy_mock = Mock()

def dummy_task_function_for_resolution(*args, **kwargs):
    dummy_mock(*args, **kwargs)


class TestDispatcher(SimpleTestCase):
    def test_dispatch_with_invalid_module_path_raises_module_not_found_error(self):
        """
        What it tests: Verifies that the dispatcher properly raises a ModuleNotFoundError 
        when given a module_path that looks valid (contains a dot) but does not actually exist.
        
        How it works:
        1. The dispatcher attempts importlib.import_module("invalid_module.path"), failing with ModuleNotFoundError.
        2. Assuming the last part of the path is the function name, it splits into module="invalid_module" and task="path".
        3. It tries to import "invalid_module", which also fails, raising a secondary ModuleNotFoundError.
        """
        payload = Payload(
            task=TaskPayload(
                backend="default",
                module_path="invalid_module.path",
                name="some_task",
                priority=0,
                queue_name="default",
                takes_context=False,
            ),
            task_id="test-id",
            enqueued_at="2026-05-12T10:00:00+00:00",
            args=[],
            kwargs={},
        )

        with self.assertRaises(ModuleNotFoundError):
            dispatch(payload)

    def test_dispatch_invalid_module_path_no_dot_raises_value_error(self):
        """
        What it tests: Ensures the dispatcher fails predictably if it receives a malformed 
        module_path that lacks any dots.
        
        How it works:
        1. The first import attempt of "invalid_module_path" fails.
        2. The code attempts to unpack module_path.rsplit(".", 1) into two variables.
        3. Because there are no dots, rsplit() returns a list of one item ["invalid_module_path"]. 
        4. This causes Python to raise a ValueError ("not enough values to unpack").
        """
        payload = Payload(
            task=TaskPayload(
                backend="default",
                module_path="invalid_module_path",
                name="some_task",
                priority=0,
                queue_name="default",
                takes_context=False,
            ),
            task_id="test-id",
            enqueued_at="2026-05-12T10:00:00+00:00",
            args=[],
            kwargs={},
        )

        with self.assertRaises(ValueError):
            dispatch(payload)

    def test_dispatch_resolves_task_name_from_module_path(self):
        """
        What it tests: Exercises the line `task_name = task_name or task_name_from_path`. It proves that 
        if the task name is empty, the dispatcher can extract the function name from the end of the module_path.
        
        How it works:
        1. Creates a payload with an empty name="" and module_path="tests.test_dispatcher.dummy_task_function_for_resolution".
        2. The first import attempt fails (because the function name is treated as part of the module path).
        3. It splits the string, successfully loading the "tests.test_dispatcher" module.
        4. The `task_name = "" or "dummy_task_function_for_resolution"` logic triggers, extracting the name.
        5. It executes the function with the provided args.
        """
        dummy_mock.reset_mock()
        payload = Payload(
            task=TaskPayload(
                backend="default",
                module_path="tests.test_dispatcher.dummy_task_function_for_resolution",
                name="",
                priority=0,
                queue_name="default",
                takes_context=False,
            ),
            task_id="test-id",
            enqueued_at="2026-05-12T10:00:00+00:00",
            args=["arg1"],
            kwargs={"kwarg1": "val1"},
        )

        dispatch(payload)

        dummy_mock.assert_called_once_with("arg1", kwarg1="val1")

