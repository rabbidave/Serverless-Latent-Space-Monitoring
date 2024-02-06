# Jimmy Neutron and Serverless Latent Space Monitoring
A series of serverless functions/resources (and Terraform) for consuming language model inputs and outputs to S3, enriching the data via sentiment analysis and topic modelling, loading to DynamoDB and subsequently monitoring for configurable deviation within the latent vector space.

Note: Support for monitoring [Text](https://www.zeroday.tools/), [Vision](https://github.com/Zoky-2020/SGA), and Multimodal Attack Non-Conformity coming soon


## ♫ The Dream of the 90's ♫ is alive in ~~Portland~~ ["a weird suite of Enterprise LLM tools"](https://github.com/users/rabbidave/projects/1) named after [Nicktoons](https://en.wikipedia.org/wiki/Nicktoons)
### by [some dude in his 30s](https://www.linkedin.com/in/davidisaacpierce)
#


<img src="https://static.wikia.nocookie.net/jimmyneutron/images/f/f2/3312414-jimmydog.jpg/revision/latest/scale-to-width-down/1000?cb=20230417181235" alt="Jimmy" title="Jimmy" width="20%">


## Description:

### Lambda1 (Jimmy Neutron.py)

    Initialization: 
        
        * Initializes clients for S3, Comprehend (as data enrichment), and DynamoDB.

    State Management:
        
        * Retrieves and updates a state record in a DynamoDB table; tracking state across invocations.

    Processing:
        
        * Writes payloads to 'S3Comprehend' and initiates Comprehend jobs for topic and sentiment analysis, with results stored in S3; thereafter loading enriched data to DynamoDB such that new records are streamed to Lambda2 via DBStreams

    IAM Permissions:
        
        * The Terraform module grants necessary permissions for S3, DynamoDB, and Comprehend interactions.
       
    Note: Ensure the 'DataAccessRoleArn' provided to Comprehend has the appropriate permissions to access S3 buckets.

### Lambda2 (Goddard, Compute!.py)

    Initialization:
        
        * Initializes S3 (for large vector storage) and SQS (for alerting); identifying and caching the most recent centroid vector from 'S3VectorStore' at initialization for easier processing and alerting via SQS.

    Processing:
        
        * Triggered by net-new DynamoDB Stream Records, whereby it encodes items with the 'text' attribute using SBERT and compares them to the cached centroid; recording a new centroid in S3 if the comparison exceeds a predefined threshold which alerts via SQS.

    IAM Permissions:
        
        * Permissions for S3, SQS, and DynamoDB interactions are included in the Terraform module's IAM policy.

### Terraform Module

    Resource Definitions:
        
        * Defines DynamoDB tables, SQS queues, and IAM roles/policies in support of both Lambda functions.

    IAM Role Policy:
        
        * Grants access to S3, DynamoDB, SQS and Comprehend.

    Security Group and Lambda Configuration:
        
        * Defines a security group for Lambda functions and references 'module.lambda_functions' for Lambda deployment specifics

### Forthcoming Changes

    Lambda1:
        
        * Better Error Handling, Logging, and Monitoring of AWS Comprehend jobs

    Lambda2:
        
        * Better Error Handling, Logging, and retry logic solving for delays in Centroid Vector availability

    TF Module:
        
        * Conserved conventions across and support for other components (e.g. input pre-processing, output post-processing, forecasting, etc) of [LatentSpace.Tools](www.latentspace.tools)
