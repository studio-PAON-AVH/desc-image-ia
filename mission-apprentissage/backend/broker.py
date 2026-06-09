import os
from dotenv import load_dotenv
from taskiq_redis import ListQueueBroker

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")

broker = ListQueueBroker(REDIS_URL, queue_name="taskiq_queue")
