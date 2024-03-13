import boto3
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import os
import datetime

# Initializations
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sqs = boto3.client('sqs')
ALERT_QUEUE_URL = os.environ['ALERT_QUEUE_URL']
S3_BUCKET = os.environ['S3VectorStore']
VECTOR_DIMENSION = 768
THRESHOLD = 0.3 * np.sqrt(VECTOR_DIMENSION)  # Adjusted threshold
NUM_CENTROIDS = 3  # Number of centroids to maintain
encoder = SentenceTransformer('bert-base-nli-mean-tokens')

# Function to find the most recent centroid keys based on timestamp
def find_latest_centroid_keys(bucket_name):
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix='centroids/')
    centroid_files = response.get('Contents', [])
    if not centroid_files:
        return []
    
    # Sort the files by LastModified date and return the keys of the most recent NUM_CENTROIDS
    latest_files = sorted(centroid_files, key=lambda x: x['LastModified'], reverse=True)[:NUM_CENTROIDS]
    return [file['Key'] for file in latest_files]

# Updated function to load the most recent centroids from S3
def load_centroids_from_s3():
    global cached_centroids
    centroid_keys = find_latest_centroid_keys(S3_BUCKET)
    cached_centroids = []
    
    if not centroid_keys:
        print("No centroid vectors found in S3, initializing with zeros.")
        cached_centroids = [np.zeros(VECTOR_DIMENSION) for _ in range(NUM_CENTROIDS)]
        return
    
    try:
        for key in centroid_keys:
            response = s3.get_object(Bucket=S3_BUCKET, Key=key)
            centroid_data = json.loads(response['Body'].read().decode('utf-8'))
            cached_centroids.append(np.array(centroid_data['vector']))
    except Exception as e:
        print(f"Error loading centroids from S3: {str(e)}")
        cached_centroids = [np.zeros(VECTOR_DIMENSION) for _ in range(NUM_CENTROIDS)]

def update_centroids_in_s3(new_centroid):
    global cached_centroids
    
    # Remove the oldest centroid if the number of centroids exceeds NUM_CENTROIDS
    if len(cached_centroids) >= NUM_CENTROIDS:
        cached_centroids = cached_centroids[1:]
    
    # Add the new centroid to the list
    cached_centroids.append(new_centroid)
    
    # Store the updated centroids in S3
    for i, centroid in enumerate(cached_centroids):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        key = f"centroids/{timestamp}_centroid_{i}.json"
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps({'vector': centroid.tolist()}))
    
    print(f"Updated centroid vectors stored in S3")

def lambda_handler(event, context):
    global cached_centroids
    
    if not cached_centroids:
        load_centroids_from_s3()
    
    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            item = record['dynamodb']['NewImage']
            text = item['text']['S']
            vector = encoder.encode([text])
            
            distances = [np.linalg.norm(vector - centroid) for centroid in cached_centroids]
            min_distance = min(distances)
            
            if min_distance > THRESHOLD:
                new_centroid = (cached_centroids[distances.index(min_distance)] + vector) / 2
                update_centroids_in_s3(new_centroid)
                
                alert_message = {
                    'text': text,
                    'distance': min_distance,
                    'threshold_exceeded': True
                }
                sqs.send_message(QueueUrl=ALERT_QUEUE_URL, MessageBody=json.dumps(alert_message))
    
    return {
        'statusCode': 200,
        'body': 'Processed successfully'
    }