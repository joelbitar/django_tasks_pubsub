# django_tasks_pubsub

PostgreSQL-backed task pub/sub for Django.

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

```python
@pubsub_task(topic="images")
def function(image_id):
    ...
```


## Development

## License
MIT