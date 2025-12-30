import redis
import json
import os
import threading
from typing import Callable, Dict

class EventBus:
    def __init__(self, host='redis', port=6379, db=0):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        self.handlers: Dict[str, list[Callable]] = {}
        self.running = False
        self.thread = None

    def publish(self, topic: str, event_data: dict):
        """Publish a dictionary as a JSON string to a topic."""
        self.redis.publish(topic, json.dumps(event_data))

    def subscribe(self, topic: str, handler: Callable):
        """Subscribe to a topic with a callback handler."""
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)
        self.pubsub.subscribe(topic)

    def start(self):
        """Start the listener thread."""
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def _listen(self):
        """Internal listener loop."""
        for message in self.pubsub.listen():
            if not self.running:
                break
            if message['type'] == 'message':
                topic = message['channel']
                try:
                    data = json.loads(message['data'])
                    if topic in self.handlers:
                        for handler in self.handlers[topic]:
                            try:
                                handler(data)
                            except Exception as e:
                                print(f"Error handling message on {topic}: {e}")
                except json.JSONDecodeError:
                    print(f"Failed to decode message on {topic}")

    def stop(self):
        """Stop the listener thread."""
        self.running = False
        self.pubsub.unsubscribe()
        self.pubsub.close()
        # Thread will exit on next message or can be left to daemon
