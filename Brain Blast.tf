# example resource policy to be applied to Lambda 2; still defining provisioning module for the DynamoDB instance and Lambda functions

resource "aws_lambda_permission" "allow_dynamodb" {
  statement_id  = "AllowDynamoDB"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.example.function_name
  principal     = "dynamodb.amazonaws.com"
  source_arn    = aws_dynamodb_table.example.stream_arn
}
