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
INPUT_TOPIC = "traffic_sign_detection_output"
OUTPUT_TOPIC = "traffic_flow_output"
SUBSCRIPTION_NAME = "traffic_flow_input_sub"

# Get topic and subscription paths
input_topic_path = publisher.topic_path(PROJECT_ID, INPUT_TOPIC)
output_topic_path = publisher.topic_path(PROJECT_ID, OUTPUT_TOPIC)
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

print(f"Initializing with project: {PROJECT_ID}")
print(f"Input topic: {INPUT_TOPIC}")
print(f"Output topic: {OUTPUT_TOPIC}")
print(f"Subscription: {SUBSCRIPTION_NAME}")

def analyze_traffic_flow(cars, traffic_lights, traffic_signs):
    # Simple traffic flow analysis based on number of objects
    car_count = len(cars)
    traffic_light_count = len(traffic_lights)
    traffic_sign_count = len(traffic_signs)
    
    # Calculate traffic density
    traffic_density = "High" if car_count > 10 else "Medium" if car_count > 5 else "Low"
    
    # Determine traffic flow status
    if traffic_light_count > 0:
        flow_status = "Controlled"
    elif traffic_sign_count > 0:
        flow_status = "Regulated"
    else:
        flow_status = "Uncontrolled"
    
    return {
        "traffic_density": traffic_density,
        "flow_status": flow_status,
        "car_count": car_count,
        "traffic_light_count": traffic_light_count,
        "traffic_sign_count": traffic_sign_count
    }

def process_message(message):
    try:
        print("Received message")
        # Decode the message
        data = json.loads(message.data.decode('utf-8'))
        print(f"Message data: {json.dumps(data, indent=2)}")
        
        # Analyze traffic flow
        traffic_flow = analyze_traffic_flow(
            data.get('Cars', []),
            data.get('Traffic_Lights', []),
            data.get('Traffic_Signs', [])
        )
        
        print(f"Traffic flow analysis: {json.dumps(traffic_flow, indent=2)}")
        
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
            'Traffic_Flow': traffic_flow
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
