import cv2
import numpy as np
import json
import base64
from google.cloud import pubsub_v1
import os
from io import BytesIO

# Initialize Pub/Sub client
publisher = pubsub_v1.PublisherClient()

# Define topic name
PROJECT_ID = 'milestone4-455221'
TOPIC_NAME = "pedestrian_detection_input"

# Get topic path
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_NAME)

def publish_message(image_path):
    try:
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            print(f"Error reading image: {image_path}")
            return

        # Convert image to base64
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        # Prepare message data
        message_data = {
            'Timestamp': '2024-03-19T12:00:00Z',
            'Car2_Location': [100, 100, 200, 200],  # Example coordinates
            'Car1_dimensions': [100, 50],  # Example dimensions
            'Car2_dimensions': [100, 50],  # Example dimensions
            'Occluded_Image_View': img_base64,
            'Occluding_Image_View': img_base64,  # Using same image for both views
            'Pedestrians': [],  # Will be filled by YOLO service
            'Cars': []  # Will be filled by YOLO service
        }

        # Publish message
        future = publisher.publish(topic_path, json.dumps(message_data).encode('utf-8'))
        future.result()
        print(f"Published message for image: {image_path}")

    except Exception as e:
        print(f"Error publishing message: {e}")

def main():
    # Get the directory of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the image
    image_path = os.path.join(script_dir, 'aerialView.png')
    
    # Publish message
    publish_message(image_path)

if __name__ == "__main__":
    main()
