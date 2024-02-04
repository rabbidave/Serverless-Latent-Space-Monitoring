import boto3
from sentence_transformers import SentenceTransformer
import numpy as np
import datetime

# Initializations
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ClusterCentroids')
pinecone.init()
sqs = boto3.client('sqs')
ALERT_QUEUE_URL = 'your_sqs_queue_url'

VECTOR_DIMENSION = 768
THRESHOLD = 0.7 * np.sqrt(VECTOR_DIMENSION)

def euclidean_distance(vec1, vec2):
    return np.linalg.norm(np.array(vec1) - np.array(vec2))

def get_centroid(attribute, value):
    filter_condition = boto3.dynamodb.conditions.Attr(attribute).eq(value)
    response = table.scan(FilterExpression=filter_condition)
    if response['Items']:
        return response['Items'][0]['vector']
    return None

def update_centroid(attribute, value, new_centroid):
    cluster_id = f"cluster_1"
    table.put_item(Item={
        attribute: value,
        'clusterID': cluster_id,
        'vector': new_centroid,
        'last_updated': str(datetime.datetime.now()),
        'num_points': 1
    })

def lambda_handler(event, context):
    encoder = SentenceTransformer('bert-base-nli-mean-tokens')
    vectors = []
    processed_records = []
# Trigger only based on changes to DynamoDB; not deletion events
    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            item = record['dynamodb']['NewImage']
            text = item['text']['S']
            topics = item['topics']['S']
            sentiment = item['sentiment']['S']
            vector = encoder.encode([text, topics, sentiment])
            vectors.append(vector)
            uuid = item['id']['S']
            pinecone.add_vector(uuid, vector)
            processed_records.append(item)
# For each new vector, compare against centroids for its sentiment, topic, and text; update centroid as needed
    for item, vector in zip(processed_records, vectors):
        sentiment = item['sentiment']['S']
        topic = item['topics']['S']
        text = item['text']['S']
        attributes = [('sentiment', sentiment), ('topic', topic), ('text', text)]
        
        for attribute, value in attributes:
            centroid = get_centroid(attribute, value)
            if centroid:
                distance = euclidean_distance(vector, centroid)
                if distance > THRESHOLD:
                    new_centroid = (np.array(centroid) + np.array(vector)) / 2
                    update_centroid(attribute, value, new_centroid.tolist())
                    alert_message = {
                        'text': text,
                        'topics': topic,
                        'sentiment': sentiment
                    }
                    sqs.send_message(QueueUrl=ALERT_QUEUE_URL, MessageBody=str(alert_message))
            else:
                update_centroid(attribute, value, vector.tolist())
    
    return {
        'statusCode': 200,
        'body': 'Processed successfully'
    }