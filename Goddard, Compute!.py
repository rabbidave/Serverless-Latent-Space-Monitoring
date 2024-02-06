import boto3
from sentence_transformers import SentenceTransformer
import numpy as np
import json
import os

# Initializations
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
sqs = boto3.client('sqs')
ALERT_QUEUE_URL = os.environ['ALERT_QUEUE_URL']
S3_BUCKET = os.environ['S3_BUCKET_NAME']

VECTOR_DIMENSION = 768
THRESHOLD = 0.7 * np.sqrt(VECTOR_DIMENSION)
encoder = SentenceTransformer('bert-base-nli-mean-tokens')

# Function to find the most recent centroid key based on timestamp
def find_latest_centroid_key(bucket_name):
    # Assumes centroid keys are stored by this function with a timestamp in their name, e.g., 'centroids/2023-01-01_centroid.json'
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix='centroids/')
    centroid_files = response.get('Contents', [])
    
    if not centroid_files:
        return None
    
    # Sort the files by LastModified date and return the key of the most recent
    latest_file = max(centroid_files, key=lambda x: x['LastModified'])
    return latest_file['Key']

# Updated function to load the most recent centroid from S3
def load_centroid_from_s3():
    global cached_centroid
    centroid_key = find_latest_centroid_key(S3_BUCKET)
    
    if not centroid_key:
        print("No centroid vector found in S3, initializing with zeros.")
        cached_centroid = np.zeros(VECTOR_DIMENSION)
        return
    
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=centroid_key)
        centroid_data = json.loads(response['Body'].read().decode('utf-8'))
        cached_centroid = np.array(centroid_data['vector'])
    except Exception as e:
        print(f"Error loading centroid from S3: {str(e)}")
        cached_centroid = np.zeros(VECTOR_DIMENSION)

def update_centroid_in_s3(new_centroid):
    # Generate a timestamped key for the new centroid
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    key = f"centroids/{timestamp}_centroid.json"
    
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps({'vector': new_centroid.tolist()}))
    print(f"Updated centroid vector stored as {key}")

def lambda_handler(event, context):
    global cached_centroid
    if cached_centroid is None:
        load_centroid_from_s3()

    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            item = record['dynamodb']['NewImage']
            text = item['text']['S']
            vector = encoder.encode([text])

            distance = euclidean_distance(vector, cached_centroid)
            if distance > THRESHOLD:
                cached_centroid = (cached_centroid + vector) / 2
                update_centroid_in_s3(cached_centroid)
                alert_message = {
                    'text': text,
                    'distance': distance,
                    'threshold_exceeded': True
                }
                sqs.send_message(QueueUrl=ALERT_QUEUE_URL, MessageBody=json.dumps(alert_message))

    return {
        'statusCode': 200,
        'body': 'Processed successfully'
    }
