import importlib
import logging
from collections.abc import Callable
from contextlib import nullcontext
from typing import Any

from django.conf import settings

logger = logging.getLogger("django_tasks_pubsub.telemetry")

DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_GETTER = "DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_GETTER"
DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_RESTORER = "DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_RESTORER"

TRACE_PROPAGATION_GETTER = DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_GETTER
TRACE_PROPAGATION_RESTORER = DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_RESTORER


def _resolve_setting(setting_names: tuple[str, ...]) -> Callable[..., Any] | None:
    for setting_name in setting_names:
        try:
            configured = getattr(settings, setting_name, None)
        except Exception:
            configured = None

        if configured is None:
            continue

        if callable(configured):
            return configured

        if isinstance(configured, str):
            import_path = configured
            module_name, _, attribute_name = import_path.rpartition(".")
            if not module_name or not attribute_name:
                continue
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                logger.exception("Failed to import telemetry hook %s", import_path)
                continue

            hook = getattr(module, attribute_name, None)
            if callable(hook):
                return hook

    return None


def get_message_trace_metadata() -> dict[str, str]:
    """Return dict metadata for pub/sub message attributes.

    The default implementation is a no-op. Applications may configure a callable via
    the Django settings hook to serialize telemetry metadata like Sentry baggage or
    OpenTelemetry propagation headers.
    """

    getter = _resolve_setting((
        DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_GETTER,
        TRACE_PROPAGATION_GETTER,
        "PUBSUB_TRACE_PROPAGATION_GETTER",
    ))
    if getter is None:
        return {}

    try:
        metadata = getter()
    except Exception:
        logger.exception("Telemetry metadata getter raised an exception")
        return {}

    if metadata is None:
        return {}

    if not isinstance(metadata, dict):
        return {}

    return {
        str(key): str(value)
        for key, value in metadata.items()
        if isinstance(key, str) and value is not None
    }


def get_trace_propagation_metadata() -> dict[str, str]:
    return get_message_trace_metadata()


def restore_trace_context(metadata: dict[str, str]) -> Any:
    """Restore tracing state from serialized message attributes.

    The configured restorer can either mutate global tracing state and return None,
    or return a context manager such as Sentry's continue_trace(...).
    """

    if not isinstance(metadata, dict):
        return None

    restorer = _resolve_setting((
        DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_RESTORER,
        TRACE_PROPAGATION_RESTORER,
        "PUBSUB_TRACE_PROPAGATION_RESTORER",
    ))
    if restorer is None:
        return None

    try:
        context = restorer(metadata)
    except Exception:
        logger.exception("Telemetry context restorer raised an exception")
        return None

    if context is None:
        return nullcontext()

    if hasattr(context, "__enter__") and hasattr(context, "__exit__"):
        return context

    return nullcontext()


__all__ = [
    "DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_GETTER",
    "DJANGO_TASKS_PUBSUB_TRACE_PROPAGATION_RESTORER",
    "TRACE_PROPAGATION_GETTER",
    "TRACE_PROPAGATION_RESTORER",
    "get_message_trace_metadata",
    "get_trace_propagation_metadata",
    "restore_trace_context",
]
