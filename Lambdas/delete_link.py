import os  # for environment variables
import json  # for JSON parsing and serialization
import boto3  # AWS SDK for Python
from botocore.exceptions import ClientError  # to catch DynamoDB errors

# Initialize DynamoDB resource (uses IAM role or AWS credentials)
dynamodb = boto3.resource('dynamodb')
# Table name configurable via environment variable (default: 'Links')
TABLE_NAME = os.environ.get('LINKS_TABLE', 'Links')


def lambda_handler(event, context):
    """
    AWS Lambda entry point: deactivates ("deletes") a link by setting its IsActive flag to False.

    Expects JSON body with:
      - LinkId (string, required)
    Optionally, you can include a UserId to verify ownership (not implemented here).

    Responses:
      200: { message: 'Link deactivated' }
      400: Malformed input
      404: Link not found
      500: Other server error
    """
    # 1. Parse and validate input parameters
    try:
        raw_body = event.get('body', {})
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        link_id = body['LinkId']  # required parameter
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing or invalid input: {e}'})
        }

    # Reference the DynamoDB table
    table = dynamodb.Table(TABLE_NAME)

    try:
        # 2. Perform update: set IsActive to False, only if the item exists
        table.update_item(
            Key={'LinkId': link_id},
            UpdateExpression='SET IsActive = :false_val',
            ExpressionAttributeValues={':false_val': False},
            ConditionExpression='attribute_exists(LinkId)'
        )
    except ClientError as e:
        # Handle conditional check failure (item doesn't exist)
        error_code = e.response['Error']['Code']
        if error_code == 'ConditionalCheckFailedException':
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Link not found'})
            }
        # Other DynamoDB error
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Unable to deactivate link: {e.response.get("Error", {}).get("Message", str(e))}'})
        }

    # 3. Return success response
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Link deactivated'})
    }

# Create a mock event with a sample LinkId
# mock_event = {
#     'body': json.dumps({
#         'LinkId': 'gjJ4OGlx'
#     })
# }

# # Call the lambda handler with the mock event
# response = lambda_handler(mock_event, None)

# # Print the response
# print(json.dumps(response, indent=2))