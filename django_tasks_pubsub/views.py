import base64
import json
import logging

logger = logging.getLogger("django_tasks_pubsub.views")

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from django_tasks_pubsub.dispatcher import dispatch
from django_tasks_pubsub.backend import Payload, TaskPayload


@method_decorator(csrf_exempt, name="dispatch")
class PubSubPushView(View):
    """
    Receives Pub/Sub push messages and dispatches them to TASK_DISPATCH_FUNCTION.

    Pub/Sub push format:
    {
      "message": {
        "data": "<base64-encoded JSON payload>",
        "messageId": "...",
        "publishTime": "..."
      },
      "subscription": "projects/.../subscriptions/..."
    }

    Returns 204 on success (Pub/Sub ACKs on any 2xx).
    Returns 400 on malformed message (no retry).
    Returns 500 on task failure (Pub/Sub will retry).
    """

    def post(self, request):
        try:
            envelope = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            logger.error("PubSubPushView: invalid JSON body")
            return HttpResponse(status=400)

        message_data = envelope.get("message", {})

        encoded_data = message_data.get("data", None)

        if encoded_data is None:
            logger.error("PubSubPushView: missing message.data")
            return HttpResponse(status=400)

        if not encoded_data:
            logger.error("PubSubPushView: empty message.data")
            return HttpResponse(status=400)

        try:
            decoded_data = base64.b64decode(encoded_data)
        except Exception as exc:
            logger.error(f"PubSubPushView: failed to decode base64 data: {encoded_data!r} error={exc!r}")
            return HttpResponse(status=400)


        try:
            payload_dict = json.loads(decoded_data)
        except Exception as exc:
            logger.error(f"PubSubPushView: failed to parse json payload: {decoded_data!r} error={exc!r}")
            return HttpResponse(status=400)

        try:
            payload = Payload(
                task=TaskPayload(
                    **payload_dict.pop("task"),
                ),
                **payload_dict,
            )
        except Exception as exc:
            logger.exception(f"PubSubPushView: failed to instantiate payload object from data: {payload_dict} error={exc!r}")
            return HttpResponse(status=400)

        logger.info(f"PubSubPushView: dispatching task_type={payload.task.name!r}")

        try:
            dispatch(payload=payload)
        except BaseException as exc:
            logger.exception(f"PubSubPushView: task failed: {payload!r} error={exc}")
            return HttpResponse(status=500)

        return HttpResponse(status=204)
