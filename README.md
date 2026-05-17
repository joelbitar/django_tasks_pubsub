# django_tasks_pubsub

Google Cloud Pub/Sub backend for Django tasks

## Installation

```bash
pip install django_tasks_pubsub
```

```python
INSTALLED_APPS = [
    ...
    "django_tasks_pubsub",
]
```

## Settings

```python
PUBSUB_PROJECT_ID = "your-google-cloud-project-id"
PUBSUB_DEFAULT_TOPIC_ID = "your-default-topic-id"

TASKS = {
    "default": {
        "BACKEND": "django_tasks_pubsub.PubSubBackend",
    }
}
```

## Usage

### Configure Django task functions
```python
from django.tasks import task

@task
def send_email(user_id):
    print(f"Sending email to {user_id}")

```

### Configure specifics for the task

#### Specify a topic

Here we configure a task that publishes to the topic "resize_images"

```python
from django.tasks import task
from django_tasks_pubsub import pubsub_task

@task
@pubsub_task(topic="resize_images")
def function(image_id):
    ...
```


## Development

## License
MIT