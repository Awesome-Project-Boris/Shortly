import os  # environment variables
import json  # JSON parsing/serialization
import boto3  # AWS SDK for Python
from botocore.exceptions import ClientError  # catch DynamoDB errors

# Initialize DynamoDB resource (uses IAM role or AWS credentials)
dynamodb = boto3.resource('dynamodb')
# Table name for Links; override via environment variable if needed
TABLE_NAME = os.environ.get('LINKS_TABLE', 'Links')


def lambda_handler(event, context):
    """
    AWS Lambda entry point: restores (reactivates) a link by setting its IsActive flag to True.

    Expects JSON body with:
      - LinkId (string, required)

    Responses:
      200: { message: 'Link restored' }
      400: Malformed input
      404: Link not found
      500: Other server error
    """
    # 1. Parse and validate input
    try:
        raw_body = event.get('body', {})
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        link_id = body['LinkId']
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing or invalid input: {e}'})
        }

    table = dynamodb.Table(TABLE_NAME)

    try:
        # 2. Update item: set IsActive to True, only if LinkId exists
        table.update_item(
            Key={'LinkId': link_id},
            UpdateExpression='SET IsActive = :true_val',
            ExpressionAttributeValues={':true_val': True},
            ConditionExpression='attribute_exists(LinkId)'
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ConditionalCheckFailedException':
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Link not found'})
            }
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Unable to restore link: {e.response.get("Error", {}).get("Message", str(e))}'})
        }

    # 3. Return success
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Link restored'})
    }
