import cv2
import numpy as np
import json
import base64
from google.cloud import pubsub_v1
import os
from ultralytics import YOLO
from io import BytesIO

# Initialize Pub/Sub client
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Define topic and subscription names
PROJECT_ID = 'milestone4-455221'
INPUT_TOPIC = "occlusion_detection_output"
OUTPUT_TOPIC = "traffic_light_detection_output"
SUBSCRIPTION_NAME = "traffic_light_detection_input_sub"

# Get topic and subscription paths
input_topic_path = publisher.topic_path(PROJECT_ID, INPUT_TOPIC)
output_topic_path = publisher.topic_path(PROJECT_ID, OUTPUT_TOPIC)
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

print(f"Initializing with project: {PROJECT_ID}")
print(f"Input topic: {INPUT_TOPIC}")
print(f"Output topic: {OUTPUT_TOPIC}")
print(f"Subscription: {SUBSCRIPTION_NAME}")

# Load YOLO model
model = YOLO('yolo11n.pt')

def process_message(message):
    try:
        print("Received message")
        # Decode the message
        data = json.loads(message.data.decode('utf-8'))
        print(f"Message data: {json.dumps(data, indent=2)}")
        
        # Get image data
        image_data = base64.b64decode(data['Occluded_Image_View'])
        image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        
        # Run YOLO detection
        results = model(image)
        
        # Process results
        traffic_light_boxes = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                if box.cls == 9:  # Traffic light class
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    traffic_light_boxes.append([float(x1), float(y1), float(x2), float(y2)])
        
        print(f"Found {len(traffic_light_boxes)} traffic lights")
        
        # Prepare output message
        output_data = {
            'Timestamp': data.get('Timestamp', ''),
            'Car2_Location': data.get('Car2_Location', []),
            'Car1_dimensions': data.get('Car1_dimensions', []),
            'Car2_dimensions': data.get('Car2_dimensions', []),
            'Occluded_Image_View': data['Occluded_Image_View'],
            'Occluding_Image_View': data.get('Occluding_Image_View', ''),
            'Pedestrians': data.get('Pedestrians', []),
            'Cars': data.get('Cars', []),
            'Occlusions': data.get('Occlusions', []),
            'Traffic_Lights': traffic_light_boxes
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
