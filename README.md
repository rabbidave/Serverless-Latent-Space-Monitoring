# Jimmy Neutron and Serverless Stepwise Latent Space Monitoring
A series of serverless stepwise functions (and Terraform) for consuming language model inputs and outputs to S3, enriching the data via sentiment analysis and topic modelling, loading to DynamoDB and subsequently monitoring for the emergence new clustered topics or sentiment within the latent vector space.


## ♫ The Dream of the 90's ♫ is alive in ~~Portland~~ ["a weird suite of Enterprise LLM tools"](https://github.com/users/rabbidave/projects/1) named after [Nicktoons](https://en.wikipedia.org/wiki/Nicktoons)
### by [some dude in his 30s](https://www.linkedin.com/in/davidisaacpierce)
#
## Utility 6) # Jimmy Neutron and Serverless Stepwise Latent Space Monitoring

<img src="https://static.wikia.nocookie.net/jimmyneutron/images/f/f2/3312414-jimmydog.jpg/revision/latest/scale-to-width-down/1000?cb=20230417181235" alt="Jimmy" title="Jimmy" width="30%">


## Description:

[Lambda 1:](https://github.com/rabbidave/Jimmy-Neutron-and-Serverless-Stepwise-Latent-Space-Monitoring/blob/main/Jimmy%20Neutron.py) SQS Consumer, Comprehend Enricher, DynamoDB Loader

Purpose: This Lambda function is designed to consume messages from an SQS queue, enrich the data using Amazon Comprehend for topic detection and sentiment analysis, and then load the enriched data into a DynamoDB table.

1) SQS Consumption - The function starts by fetching messages from an SQS queue (event['Records']). This means that this Lambda is triggered whenever there are new messages in the SQS queue.

2) Data Enrichment - For every record from SQS, the function:
    * Writes the data to S3.
    * Starts a topic detection job using Amazon Comprehend if enough records have been accumulated.
    * Once topic detection is done, it starts a sentiment detection job.
    * After sentiment detection, the data (text, topics, sentiment) is enriched and ready for storage.

3) DynamoDB Loading - The enriched data is then loaded into a DynamoDB table.

[Lambda 2:](https://github.com/rabbidave/Jimmy-Neutron-and-Serverless-Stepwise-Latent-Space-Monitoring/blob/main/Goddard%2C%20Compute!.py) DynamoDB Stream Consumer, Vector Encoder, Centroid Comparator

Purpose: This Lambda function is designed to consume data from a DynamoDB stream, encode the data into vectors, compare these vectors to existing centroids, and update centroids or send alerts as necessary.

1) DynamoDB Stream Consumption - The function is triggered by changes to the DynamoDB table. This means whenever a new item is added (or an existing item is modified) in the DynamoDB table, this Lambda function will be invoked.

2) Data Encoding - For every new or modified item in the DynamoDB table, the function:
    * Encodes the text, topics, and sentiment fields into a 768-dimensional vector using SBERT.
    * Loads these vectors into Pinecone.

3) Centroid Comparison - For each encoded vector:
    * The function fetches the corresponding centroid from the DynamoDB table.
    * If the centroid exists, it calculates the distance between the new vector and the centroid.
    * If the distance exceeds a threshold, the centroid is updated, and an alert is sent to an SQS queue.
    * If no centroid exists for the attribute-value pair, a new centroid is created.

Terraform Module:

1) Script Provisions DynamoDB instance alongside Lambda 1 & Lambda 2

2) Applies requisite Resource Policy allowing Dynamo DB Streams to invoke Lambda 2

## Rationale:

1) User experience, instrumentation, and metadata capture are crucial to the adoption of LLMs for orchestration of [multi-modal agentic systems](https://en.wikipedia.org/wiki/Multi-agent_system); predicting the range of possible values at set prediction intervals allows for early warning of LLM Drift
## Intent:
Make it easier to monitor inputs and outputs to/from language models; eventually latent space applications as tokenization layers become less common


____________

To do:

Lambda 1)

Avoid Duplicate Entries or Missing Values-

The function load_to_dynamodb writes to DynamoDB without checking for duplicates.
Planned Change: Before writing to DynamoDB, check if the record already exists and decide whether to update, skip, or throw an error.

Limit AWS API Calls in a Loop-

The function process_record still lists objects and starts jobs in loops.
Planned Change: Consider using pagination for s3.list_objects_v2 to handle a large number of objects and avoid making too many API calls.

Optimize AWS Comprehend Job Starts-

The function process_record starts a Comprehend job for every 1000 records within the loop.
Planned Change: Consider aggregating the records and starting the job once after the loop.


Lambda 2) 

Improve Error Handling to be AWS Service Specific

Have GPT4 suggest any other opportunties for improvement

etc



Terraform Module)

Provisioning; currently has none

Identify if other policies are needed outside the resource policy allowing Lambda 2 invocation by DynamoDB Streams
