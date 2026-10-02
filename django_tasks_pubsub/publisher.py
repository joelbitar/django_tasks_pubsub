from google.cloud import pubsub_v1

_publisher: pubsub_v1.PublisherClient | None = None


def get_publisher():
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
    return _publisher


def publish(topic: str, data: bytes, attributes: dict[str, str] | None = None):
    publish_kwargs = {"topic": topic, "data": data}
    if attributes is not None:
        publish_kwargs["attributes"] = attributes
    get_publisher().publish(**publish_kwargs)
