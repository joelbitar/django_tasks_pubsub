from django.test import SimpleTestCase
from django.urls import resolve, reverse

from django_tasks_pubsub.views import PubSubPushView


class TestUrls(SimpleTestCase):
    def test_pubsub_push_url_resolves_to_correct_view(self):
        """
        What it tests: Verifies that the path "/pubsub/push/" correctly maps to the PubSubPushView.
        
        How it works:
        1. Uses Django's `resolve` function to parse the path "/pubsub/push/".
        2. We explicitly pass `urlconf="django_tasks_pubsub.urls"` so it only evaluates this app's URLs.
        3. We assert that the `view_class` of the resolved function matches `PubSubPushView`.
        """
        resolver_match = resolve("/pubsub/push/", urlconf="django_tasks_pubsub.urls")
        self.assertEqual(resolver_match.func.view_class, PubSubPushView)

    def test_pubsub_push_url_reverses_correctly(self):
        """
        What it tests: Verifies that the named URL "pubsub_push" properly builds the path "/pubsub/push/".
        
        How it works:
        1. Uses Django's `reverse` function to construct a path from the name `"pubsub_push"`.
        2. We pass `urlconf="django_tasks_pubsub.urls"` to use the local routing.
        3. We assert that the resulting URL string is exactly "/pubsub/push/".
        """
        url = reverse("pubsub_push", urlconf="django_tasks_pubsub.urls")
        self.assertEqual(url, "/pubsub/push/")
