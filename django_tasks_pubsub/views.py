import base64
import json
import logging

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
    Returns 500 on task failure (Pub/Sub will retry).
    Returns 400 on malformed message (no retry).
    """

    def post(self, request):
        try:
            envelope = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            logging.error("PubSubPushView: invalid JSON body")
            return HttpResponse(status=400)

        encoded_data = envelope.get("message", {}).get("data", "")
        if not encoded_data:
            logging.error("PubSubPushView: missing message.data")
            return HttpResponse(status=400)

        try:
            payload_dict = json.loads(base64.b64decode(encoded_data))
        except Exception as exc:
            logging.error(f"PubSubPushView: failed to decode message: {exc}")
            return HttpResponse(status=400)

        try:
            payload = Payload(
                task=TaskPayload(
                    **payload_dict.pop("task"),
                ),
                **payload_dict,
            )
        except Exception as exc:
            logging.exception(f"PubSubPushView: failed to create payload: {exc}")
            return HttpResponse(status=400)

        logging.info(f"PubSubPushView: dispatching task_type={payload.task.name!r}")

        try:
            dispatch(payload=payload)
        except BaseException as exc:
            logging.exception(f"PubSubPushView: task failed: {payload!r} error={exc}")
            return HttpResponse(status=500)

        return HttpResponse(status=204)
