variable "region" {}
variable "dynamodb_name" {}
variable "environment_name" {}
variable "vpc_id" {}
variable "subnet_ids" {}
variable "tags" {
  default = {}
}
variable "s3_bucket_arn" {}

provider "aws" {
  region = var.region
}

module "dynamodb_table" {
  source = "terraform-aws-modules/dynamodb-table/aws"

  name         = var.dynamodb_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attributes = [
    {
      name = "id"
      type = "S"
    }
  ]

  tags = merge(var.tags, { Name = var.dynamodb_name })
}

resource "aws_sqs_queue" "alert_queue" {
  name = "alert-queue-${var.environment_name}"
  tags = merge(var.tags, { Name = "alert-queue-${var.environment_name}" })
}

resource "aws_sqs_queue" "deadletter_queue" {
  name = "deadletter-queue-${var.environment_name}"
  tags = merge(var.tags, { Name = "deadletter-queue-${var.environment_name}" })
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda_${var.environment_name}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_access_policy_${var.environment_name}"
  role = aws_iam_role.iam_for_lambda.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "s3:PutObject",
          "s3:GetObject",
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "comprehend:StartTopicsDetectionJob",
          "comprehend:DescribeTopicsDetectionJob",
        ],
        Resource = [
          module.dynamodb_table.this_table_arn,
          var.s3_bucket_arn,
          aws_sqs_queue.alert_queue.arn,
          aws_sqs_queue.deadletter_queue.arn,
        ]
      },
    ]
  })
}

resource "aws_security_group" "sg" {
  name        = "lambda-sg-${var.environment_name}"
  description = "Security group for Lambda functions in ${var.environment_name}"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Note: The "module.lambda_functions" referenced below assumes a custom module that you need to define.
# It should encapsulate the creation of Lambda functions, accepting configuration parameters for each function.
module "lambda_functions" {
  source = "./modules/lambda"

  lambda_configs = [
    {
      name             = "jimmyneutron"
      handler          = "jimmyneutron.handler"
      filename         = "jimmyneutron.zip"
      source_code_hash = filebase64sha256("jimmyneutron.zip")
      environment_vars = {
        DYNAMODB_TABLE = module.dynamodb_table.this_table_name
      }
      security_group_ids = [aws_security_group.sg.id]
      subnet_ids         = var.subnet_ids
    },
    {
      name             = "goddardcompute"
      handler          = "goddardcompute.handler"
      filename         = "goddardcompute.zip"
      source_code_hash = filebase64sha256("goddardcompute.zip")
      environment_vars = {
        ALERT_QUEUE_URL = aws_sqs_queue.alert_queue.url
      }
      security_group_ids = [aws_security_group.sg.id]
      subnet_ids         = var.subnet_ids
    }
  ]

  role_arn = aws_iam_role.iam_for_lambda.arn
}

output "dynamodb_table_name" {
  value = module.dynamodb_table.this_table_name
}

output "alert_queue_url" {
  value = aws_sqs_queue.alert_queue.url
}

output "deadletter_queue_url" {
  value = aws_sqs_queue.deadletter_queue.url
}

output "iam_for_lambda_arn" {
  value = aws_iam_role.iam_for_lambda.arn
}
