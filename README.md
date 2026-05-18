# django_tasks_pubsub

Google Cloud Pub/Sub backend for Django tasks

## Installation

### Package manager

#### pip
```bash
pip install django_tasks_pubsub
```

#### uv
```bash
uv add django_tasks_pubsub
```

### Add to INSTALLED_APPS
```python
INSTALLED_APPS = [
    ...
    "django_tasks_pubsub",
]
```

## Settings

### Add required Google Cloud Pub/Sub settings
```python
PUBSUB_PROJECT_ID = "your-google-cloud-project-id"
PUBSUB_DEFAULT_TOPIC_ID = "your-default-topic-id"
```

### Add the backend to the TASKS setting

```python
TASKS = {
    "default": {
        "BACKEND": "django_tasks_pubsub.PubSubBackend",
    }
}
```

## URLs

In order to receive push messages from Google Cloud Pub/Sub, you need to register the endpoint in your project's `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    ...
    path("", include("django_tasks_pubsub.urls")),
]
```

This will expose the endpoint at `/pubsub/push/`. You should configure your Google Cloud Pub/Sub push subscription to use this endpoint (e.g. `https://your-domain.com/pubsub/push/`).

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

To specify a topic, you need to decorate the task with @task and @pubsub_task(topic="topic-name")
in this order:

```python
from django.tasks import task
from django_tasks_pubsub import pubsub_task


@task
@pubsub_task(topic="images")
def function(image_id):
    ...
```


## Development

## License
MIT