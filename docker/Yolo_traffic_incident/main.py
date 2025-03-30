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
INPUT_TOPIC = "traffic_flow_output"
OUTPUT_TOPIC = "traffic_incident_output"
SUBSCRIPTION_NAME = "traffic_incident_input_sub"

# Get topic and subscription paths
input_topic_path = publisher.topic_path(PROJECT_ID, INPUT_TOPIC)
output_topic_path = publisher.topic_path(PROJECT_ID, OUTPUT_TOPIC)
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

print(f"Initializing with project: {PROJECT_ID}")
print(f"Input topic: {INPUT_TOPIC}")
print(f"Output topic: {OUTPUT_TOPIC}")
print(f"Subscription: {SUBSCRIPTION_NAME}")

def detect_traffic_incidents(cars, occlusions, traffic_flow):
    incidents = []
    
    # Check for high traffic density
    if traffic_flow['traffic_density'] == 'High':
        incidents.append({
            'type': 'congestion',
            'severity': 'high',
            'description': 'Heavy traffic congestion detected'
        })
    
    # Check for pedestrian-vehicle conflicts
    if len(occlusions) > 0:
        incidents.append({
            'type': 'pedestrian_conflict',
            'severity': 'medium',
            'description': 'Pedestrian-vehicle conflict detected'
        })
    
    # Check for traffic control issues
    if traffic_flow['flow_status'] == 'Uncontrolled' and len(cars) > 5:
        incidents.append({
            'type': 'control_issue',
            'severity': 'medium',
            'description': 'Traffic control system may be needed'
        })
    
    return incidents

def process_message(message):
    try:
        print("Received message")
        # Decode the message
        data = json.loads(message.data.decode('utf-8'))
        print(f"Message data: {json.dumps(data, indent=2)}")
        
        # Detect traffic incidents
        incidents = detect_traffic_incidents(
            data.get('Cars', []),
            data.get('Occlusions', []),
            data.get('Traffic_Flow', {})
        )
        
        print(f"Detected incidents: {json.dumps(incidents, indent=2)}")
        
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
            'Traffic_Lights': data.get('Traffic_Lights', []),
            'Traffic_Signs': data.get('Traffic_Signs', []),
            'Traffic_Flow': data.get('Traffic_Flow', {}),
            'Incidents': incidents
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
