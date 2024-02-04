# example resource policy to be applied to Lambda 2; still defining provisioning module for the DynamoDB instance and Lambda functions
provider "aws" {
  region = var.region
}

module "dynamodb_table" {
  source = "terraform-aws-modules/dynamodb-table/aws"

  name           = var.dynamodb_name
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity
  hash_key       = "id"

  attributes = [
    {
      name = "id"
      type = "S"
    }
  ]

  tags = merge(var.tags, { Name = var.dynamodb_name })
}

resource "aws_lambda_function" "jimmyneutron" {
  filename         = "jimmyneutron.zip"
  function_name    = "jimmyneutron"
  role             = aws_iam_role.iam_for_lambda.arn
  handler          = "jimmyneutron.handler"
  runtime          = "python3.8"
  source_code_hash = filebase64sha256("jimmyneutron.zip")

  environment {
    variables = {
      DYNAMODB_TABLE = module.dynamodb_table.this_table_name
    }
  }

  vpc_config {
    security_group_ids = [aws_security_group.sg.id]
    subnet_ids         = var.subnet_ids
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = " lambda:InvokeFunction"
  function_name = aws_lambda_function.jimmyneutron.function_name
  principal     = "apigateway.amazonaws.com"
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_sqs_queue" "alert_queue" {
  name                       = "alert_queue"
  delay_seconds              = 0
  max_message_size            = 2048
  message_retention_seconds   = 86400
  receive_wait_time_seconds   = 0
  visibility_timeout_seconds  = 0
  enable_messages_delete_on_receive = false

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.deadletter_queue.arn
    maxReceiveCount     = 3
  })

  tags = merge(var.tags, { Name = "alert_queue" })
}

resource "aws_sqs_queue" "deadletter_queue" {
  name = "deadletter_queue"

  tags = merge(var.tags, { Name = "deadletter_queue" })
}

resource "aws_lambda_event_source_mapping" "goddardcompute" {
  event_source_arn  = module.dynamodb_table.this_table_arn
  function_name     = aws_lambda_function.goddardcompute.function_name
  starting_position = "LATEST"
  enabled           = true
}

resource "aws_lambda_function" "goddardcompute" {
  filename         = "goddardcompute.zip"
  function_name    = "goddardcompute"
  role             = aws_iam_role.iam_for_lambda.arn
  handler          = "goddardcompute.handler"
  runtime          = "python3.8"
  source_code_hash = filebase64sha256("goddardcompute.zip")

  environment {
    variables = {
      ALERT_QUEUE_URL = aws_sqs_queue.alert_queue.id
    }
  }

  vpc_config {
    security_group_ids = [aws_security_group.sg.id]
    subnet_ids         = var.subnet_ids
  }
}

resource "aws_security_group" "sg" {
  name        = "allow_all"
  description = "Allow all inbound traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}