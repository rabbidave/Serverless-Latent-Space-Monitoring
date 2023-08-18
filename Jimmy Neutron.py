import boto3
import json
import logging

# AWS services
s3 = boto3.client('s3')
comprehend = boto3.client('comprehend')
dynamodb = boto3.resource('dynamodb')

# Configurations loaded from environment variables or configuration files
S3_BUCKET_NAME = 'YourS3BucketName'
DYNAMODB_TABLE_NAME = 'MyDynamoDBTable'
STATE_TABLE_NAME = 'LambdaStateTable'
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
state_table = dynamodb.Table(STATE_TABLE_NAME)
PROMPT_QUEUE_ARN = 'arn:aws:sqs:region:account-id:prompt-queue-name'
MODEL_OUTPUT_QUEUE_ARN = 'arn:aws:sqs:region:account-id:model-output-queue-name'

logging.basicConfig(level=logging.ERROR)

def get_state():
    """Retrieve the state from DynamoDB."""
    return state_table.get_item(Key={'id': 'lambda_state'})

def write_to_s3(payload, source, record_count):
    """Write record payload to S3."""
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=f"{source}/{record_count}.json", Body=json.dumps(payload))

def start_topic_detection(source):
    """Start a topic detection job."""
    comprehend.start_topics_detection_job(
        InputDataConfig={'S3Uri': f's3://{S3_BUCKET_NAME}/{source}/', 'InputFormat': 'ONE_DOC_PER_LINE'},
        OutputDataConfig={'S3Uri': f's3://{S3_BUCKET_NAME}/output/'},
        DataAccessRoleArn='YourRoleArn',
        JobName='TopicModelingJob',
        LanguageCode='en'
    )

def start_sentiment_detection(job_key):
    """Start a sentiment detection job."""
    comprehend.start_sentiment_detection_job(
        InputDataConfig={'S3Uri': f's3://{S3_BUCKET_NAME}/output/{job_key}', 'InputFormat': 'ONE_DOC_PER_LINE'},
        OutputDataConfig={'S3Uri': f's3://{S3_BUCKET_NAME}/output_sentiment/'},
        DataAccessRoleArn='YourRoleArn',
        LanguageCode='en'
    )

def load_to_dynamodb(payload, text, topics, sentiment, source):
    """Load enriched data to DynamoDB."""
    table.put_item(Item={
        'id': payload['metadata']['uuid'],
        'timestamp': payload['metadata']['timestamp'],
        'text': text,
        'topics': topics,
        'sentiment': sentiment,
        'source': source
    })

def update_state(record_count, context):
    """Update the state in DynamoDB after processing records."""
    state_table.put_item(Item={
        'id': 'lambda_state',
        'record_count': record_count,
        'last_run_timestamp': context.get('invoked_function_arn', {}).get('ApproximateInvocationDateTime', 0)
    })

def process_record(record, record_count, last_run_timestamp, context):
    """Process an individual SQS record."""
    source_queue_arn = record.get('eventSourceARN')
    if not source_queue_arn:
        logging.error("eventSourceARN not found in the record.")
        return record_count

    payload = json.loads(record['body'])
    text = payload['text']
    source = 'model_input' if source_queue_arn == PROMPT_QUEUE_ARN else 'model_output'

    write_to_s3(payload, source, record_count)
    record_count += 1

    if record_count >= 1000:
        start_topic_detection(source)
        record_count = 0

    topic_jobs = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix='output/')
    for job in topic_jobs.get('Contents', []):
        job_timestamp = job['LastModified'].timestamp()
        if last_run_timestamp < job_timestamp:
            result_data = s3.get_object(Bucket=S3_BUCKET_NAME, Key=job['Key'])
            topic_content = json.loads(result_data['Body'].read().decode('utf-8'))
            job_key = job['Key']

            start_sentiment_detection(job_key)

    sentiment_jobs = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix='output_sentiment/')
    for job in sentiment_jobs.get('Contents', []):
        job_timestamp = job['LastModified'].timestamp()
        if last_run_timestamp < job_timestamp:
            result_data = s3.get_object(Bucket=S3_BUCKET_NAME, Key=job['Key'])
            sentiment_content = json.loads(result_data['Body'].read().decode('utf-8'))
            topics = ', '.join([topic['Topic'] for topic in sentiment_content.get('Topics', [])])
            sentiment = sentiment_content.get('Sentiment', 'N/A')

            load_to_dynamodb(payload, text, topics, sentiment, source)

    # Update state after processing a record
    update_state(record_count, context)

    return record_count

def lambda_handler(event, context):
    try:
        state = get_state()
        record_count = state.get('Item', {}).get('record_count', 0)
        last_run_timestamp = state.get('Item', {}).get('last_run_timestamp', 0)

        for record in event['Records']:
            record_count = process_record(record, record_count, last_run_timestamp, context)

        update_state(record_count, context)

        return {
            'statusCode': 200,
            'body': json.dumps('Data processed and topic modeling and sentiment analysis jobs started if needed!')
        }

    except Exception as e:
        logging.error(f"Error processing the lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"An error occurred: {str(e)}")
        }
