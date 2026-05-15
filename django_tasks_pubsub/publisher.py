from google.cloud import pubsub_v1

_publisher: pubsub_v1.PublisherClient | None = None


def get_publisher():
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
    return _publisher


def publish(topic: str, data: bytes):
    get_publisher().publish(topic=topic, data=data)
