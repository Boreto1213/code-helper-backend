import os
from confluent_kafka import Producer
import json

_conf = {
    'bootstrap.servers': os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    'client.id': 'webhook-producer'
}
producer = Producer(_conf)

def delivery_report(err, msg):
    if err:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

def send_message(topic: str, data: dict):
    """
    Send a message to a Kafka topic
    
    Args:
        topic: Kafka topic to send the message to
        data: Dictionary containing the message data
    """
    payload = json.dumps(data).encode('utf-8')
    producer.produce(topic, payload, callback=delivery_report)
    producer.flush()  # in real apps, you may batch and flush less often