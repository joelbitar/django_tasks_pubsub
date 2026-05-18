from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from django_tasks_pubsub import publisher


class TestPublisher(SimpleTestCase):
    def setUp(self):
        # Reset the global _publisher variable before each test
        publisher._publisher = None

    @patch("django_tasks_pubsub.publisher.pubsub_v1.PublisherClient")
    def test_get_publisher_creates_new_instance_when_none(self, mock_publisher_client_class):
        mock_instance = Mock()
        mock_publisher_client_class.return_value = mock_instance

        client = publisher.get_publisher()

        self.assertEqual(client, mock_instance)
        mock_publisher_client_class.assert_called_once()
        self.assertEqual(publisher._publisher, mock_instance)

    @patch("django_tasks_pubsub.publisher.pubsub_v1.PublisherClient")
    def test_get_publisher_returns_existing_instance(self, mock_publisher_client_class):
        existing_mock = Mock()
        publisher._publisher = existing_mock

        client = publisher.get_publisher()

        self.assertEqual(client, existing_mock)
        mock_publisher_client_class.assert_not_called()

    @patch("django_tasks_pubsub.publisher.get_publisher")
    def test_publish_calls_publisher_client_publish_method(self, mock_get_publisher):
        mock_client = Mock()
        mock_get_publisher.return_value = mock_client

        topic = "test-topic"
        data = b"test-data"

        publisher.publish(topic=topic, data=data)

        mock_get_publisher.assert_called_once()
        mock_client.publish.assert_called_once_with(topic=topic, data=data)
