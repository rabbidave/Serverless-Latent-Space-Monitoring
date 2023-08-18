# Jimmy Neutron and Serverless Stepwise Latent Space Monitoring
 A series of serverless stepwise functions for consuming language model inputs and outputs to S3, enriching the data via sentiment analysis and topic modelling, loading to DynamoDB and subsequently monitoring for the emergence new clustered topics or sentiment within the latent vector space.


Lambda #1 does the following:

1) Triggered by new records on either or both SQS queues.
2) Writes the SQS records to an S3 store, adding a field indicating the source queue.
3) Evaluates against threshold to process data landing on S3; initiates topic and sentiment enrichments
6) Enriched Data is loaded to DynamoDB

Lambda #2 does x, y, and z:
1)
2)
3)

Terraform Script Provisions DynamoDB instance

____________
To do:

Avoid Duplicate Entries or Missing Values-

    The function load_to_dynamodb writes to DynamoDB without checking for duplicates.
    Planned Change: Before writing to DynamoDB, check if the record already exists and decide whether to update, skip, or throw an error.

Limit AWS API Calls in a Loop-

    The function process_record still lists objects and starts jobs in loops.
    Planned Change: Consider using pagination for s3.list_objects_v2 to handle a large number of objects and avoid making too many API calls.

Optimize AWS Comprehend Job Starts-

    The function process_record starts a Comprehend job for every 1000 records within the loop.
    Planned Change: Consider aggregating the records and starting the job once after the loop.