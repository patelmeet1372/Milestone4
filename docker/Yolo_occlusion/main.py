import cv2
import numpy as np
import json
import base64
from google.cloud import pubsub_v1
import os
from io import BytesIO

# Initialize Pub/Sub client
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Define topic and subscription names
PROJECT_ID = 'milestone4-455221'
INPUT_TOPIC = "car_detection_output"
OUTPUT_TOPIC = "occlusion_detection_output"
SUBSCRIPTION_NAME = "occlusion_detection_input_sub"

# Get topic and subscription paths
input_topic_path = publisher.topic_path(PROJECT_ID, INPUT_TOPIC)
output_topic_path = publisher.topic_path(PROJECT_ID, OUTPUT_TOPIC)
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

print(f"Initializing with project: {PROJECT_ID}")
print(f"Input topic: {INPUT_TOPIC}")
print(f"Output topic: {OUTPUT_TOPIC}")
print(f"Subscription: {SUBSCRIPTION_NAME}")

def calculate_iou(box1, box2):
    # Calculate intersection
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    if x2 < x1 or y2 < y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    
    # Calculate union
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = box1_area + box2_area - intersection
    
    return intersection / union

def process_message(message):
    try:
        print("Received message in occlusion service")
        # Decode the message
        data = json.loads(message.data.decode('utf-8'))
        print(f"Message data: {json.dumps(data, indent=2)}")
        
        # Get image data
        image_data = base64.b64decode(data['Image'])
        image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        
        # Get detections
        cars = data.get('Cars', [])
        pedestrians = data.get('Pedestrians', [])
        
        print(f"Found {len(cars)} cars and {len(pedestrians)} pedestrians")
        
        # Find occlusions
        occlusions = []
        for car in cars:
            for pedestrian in pedestrians:
                iou = calculate_iou(car, pedestrian)
                if iou > 0.1:  # Threshold for occlusion
                    occlusions.append({
                        'car': car,
                        'pedestrian': pedestrian,
                        'iou': float(iou)
                    })
        
        print(f"Found {len(occlusions)} occlusions")
        
        # Prepare output message
        output_data = {
            'Timestamp': data.get('Timestamp', ''),
            'Image': data['Image'],
            'Cars': cars,
            'Pedestrians': pedestrians,
            'Occlusions': occlusions
        }
        
        # Publish result
        future = publisher.publish(output_topic_path, json.dumps(output_data).encode('utf-8'))
        future.result()
        print("Published result to output topic")
        
        # Acknowledge the message
        message.ack()
        print("Acknowledged message")
        
    except Exception as e:
        print(f"Error processing message: {e}")
        message.ack()

def main():
    print(f"Starting to listen for messages on {subscription_path}")
    
    # Start receiving messages
    streaming_pull_future = subscriber.subscribe(
        subscription_path,
        callback=process_message
    )
    
    try:
        streaming_pull_future.result()
    except Exception as e:
        print(f"Error in subscription: {e}")
        streaming_pull_future.cancel()

if __name__ == "__main__":
    main()
