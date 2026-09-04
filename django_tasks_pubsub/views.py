import base64
import json
import logging
from typing import Union

from django.core.cache import cache

logger = logging.getLogger("django_tasks_pubsub.views")

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

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

        cache_key, forced_response = self.idempotency_check(payload=payload)
        if forced_response is not None and isinstance(forced_response, HttpResponse):
            return forced_response

        logger.info(f"PubSubPushView: dispatching task {cache_key or '___'} task_type={payload.task.name!r}")

        try:
            dispatch(payload=payload)
        except BaseException as exc:
            logger.exception(f"PubSubPushView: task {cache_key or '___'} failed: {payload!r} error={exc}")

            if cache_key:
                cache.delete(cache_key)

            return HttpResponse(status=500)

        # Mark as Done for 7 days
        if cache_key:
            logger.info(f"PubSubPushView: marking as done task {cache_key or '___'} task_type={payload.task.name!r}")
            cache.set(cache_key, "DONE", timeout=604800)

        return HttpResponse(status=204)

    def idempotency_check(self, payload: Payload) -> tuple[
        str, Union[bool, None, HttpResponse]
    ]:
        """
        return
            cache key
            True if we should process the task
        """

        if not (cache_key_prefix := getattr(settings, 'PUBSUB_CACHE_PREFIX', None)):
            return '', None

        cache_key = f"{cache_key_prefix}:{payload.task.name}:{payload.task_id}"

        logger.info(f"Task {payload.task_id}, adding to cache.")
        
        acquired = cache.add(
            cache_key,
            "PROCESSING",
            timeout=600
        )

        if not acquired:
            current_state = cache.get(cache_key)

            if current_state == "DONE":
                logger.info(f"Task {payload.task_id} already processed. ACKing.")
                # 200 OK tells Pub/Sub: "We got it, don't send it again."
                return cache_key, HttpResponse(status=200)

            elif current_state == "PROCESSING":
                logger.info(f"Task {payload.task_id} currently processing elsewhere. NACKing.")
                # 409 Conflict tells Pub/Sub: "Try again later."
                return cache_key, HttpResponse(status=409)

            else:
                # The key expired between cache.add() and cache.get(). Retry later.
                return cache_key, HttpResponse(status=409)
        
        logger.info(f"Task {payload.task_id} ready for processing")
        
        return cache_key, True
