import boto3
import pinecone
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer
import numpy as np
import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ClusterCentroids')
pinecone.init()  # initialize pinecone
sqs = boto3.client('sqs')
ALERT_QUEUE_URL = 'your_sqs_queue_url'  # Replace with your SQS queue URL

VECTOR_DIMENSION = 768  # SBERT produces a 768-dimensional vector
THRESHOLD = 0.7 * np.sqrt(VECTOR_DIMENSION)  # 70% of the maximum possible distance

def euclidean_distance(vec1, vec2):
    return np.linalg.norm(np.array(vec1) - np.array(vec2))

def get_centroid(attribute, value):
    # Retrieve the centroid for a given attribute and value
    filter_condition = boto3.dynamodb.conditions.Attr(attribute).eq(value)
    response = table.scan(FilterExpression=filter_condition)
    if response['Items']:
        return response['Items'][0]['vector']
    return None

def update_centroid(attribute, value, new_centroid):
    # Update or add the centroid for the given attribute and value
    cluster_id = f"cluster_1"  # Assuming a single cluster for simplicity
    table.put_item(Item={
        attribute: value,
        'clusterID': cluster_id,
        'vector': new_centroid,
        'last_updated': str(datetime.datetime.now()),
        'num_points': 1  # This can be incremented if updating an existing centroid
    })

def lambda_handler(event, context):
    # Initialize the SBERT encoder
    encoder = SentenceTransformer('bert-base-nli-mean-tokens')
    
    # Extract new records from the event
    new_records = event['Records']
    vectors = []
    
    for record in new_records:
        item = record['dynamodb']['NewImage']
        
        # Extract fields
        text = item['text']['S']
        topics = item['topics']['S']
        sentiment = item['sentiment']['S']
        
        # Encode the fields into a 768-dimensional latent vector space
        vector = encoder.encode([text, topics, sentiment])
        vectors.append(vector)
        
        # Load all new vectors to pinecone
        uuid = item['id']['S']
        pinecone.add_vector(uuid, vector)
    
    # For each new vector, compare against centroids for its sentiment, topic, and text
    for record, vector in zip(new_records, vectors):
        sentiment = record['dynamodb']['NewImage']['sentiment']['S']
        topic = record['dynamodb']['NewImage']['topics']['S']
        text = record['dynamodb']['NewImage']['text']['S']
        
        attributes = [('sentiment', sentiment), ('topic', topic), ('text', text)]
        
        for attribute, value in attributes:
            centroid = get_centroid(attribute, value)
            
            if centroid:
                distance = euclidean_distance(vector, centroid)
                
                # If distance is beyond the threshold, update the centroid and publish to the alert SQS queue
                if distance > THRESHOLD:
                    # Calculate the new centroid
                    new_centroid = (np.array(centroid) + np.array(vector)) / 2
                    update_centroid(attribute, value, new_centroid.tolist())
                    
                    alert_message = {
                        'text': text,
                        'topics': topic,
                        'sentiment': sentiment
                    }
                    sqs.send_message(QueueUrl=ALERT_QUEUE_URL, MessageBody=str(alert_message))
            else:
                # If no centroid exists for this attribute-value pair, create one
                update_centroid(attribute, value, vector.tolist())
    
    return {
        'statusCode': 200,
        'body': 'Processed successfully'
    }
