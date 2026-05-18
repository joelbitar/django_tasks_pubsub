from django.urls import path

from .views import PubSubPushView

app_name = "django_tasks_pubsub"

urlpatterns = [
    path("push/", PubSubPushView.as_view(), name="pubsub_push"),
]
