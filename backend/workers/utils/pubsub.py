import redis
import json

def publish_event(event_type: str, payload: dict, channel: str = "notifications"):
    """Publie un événement générique dans Redis."""
    r = redis.Redis(host='redis', port=6379, db=0)
    message = {"type": event_type, **payload}
    r.publish(channel, json.dumps(message))