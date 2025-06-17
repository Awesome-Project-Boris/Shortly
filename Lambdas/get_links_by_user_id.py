import os
import json
import boto3
import decimal
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB resource

dynamodb = boto3.resource('dynamodb')
# Table name and optional GSI name from environment
TABLE_NAME = os.environ.get('LINKS_TABLE', 'Links')
INDEX_NAME = os.environ.get('LINKS_USER_INDEX', 'UserId-index')

def _decimal_default(obj):
    """JSON serializer for DynamoDB Decimal types."""
    if isinstance(obj, decimal.Decimal):
        # Convert to int when possible, otherwise to float
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def handler(event, context):
    """
    AWS Lambda handler to retrieve all links created by a user.

    Expects JSON body with:
      - UserId (string, required)

    If a GSI named `UserId-index` exists on the Links table, it will use Query;
    otherwise it falls back to a full Scan with a filter on UserId.
    Returns 200 with `links` array on success, or 4xx on error.
    """
    # Parse and validate input
    try:
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)
        user_id = body['UserId']
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing or invalid input: {str(e)}'})
        }

    table = dynamodb.Table(TABLE_NAME)
    try:
        # Try querying by GSI
        response = table.query(
            IndexName=INDEX_NAME,
            KeyConditionExpression=Key('UserId').eq(user_id)
        )
        links = response.get('Items', [])
    except table.meta.client.exceptions.ResourceNotFoundException:
        # GSI not found, fallback to scan
        scan_kwargs = {
            'FilterExpression': Attr('UserId').eq(user_id)
        }
        response = table.scan(**scan_kwargs)
        # response = table.scan(**scan_kwargs)
        links = response.get('Items', [])
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error fetching links: {str(e)}'})
        }

    # Respond, converting Decimal types
    return {
        'statusCode': 200,
        'body': json.dumps({'links': links}, default=_decimal_default)
    }

# Create mock event with test user ID
test_event = {
    'body': json.dumps({
        'UserId': '894980c8-e8a6-4921-9bb0-f917671caa65'
    })
}

# Call the lambda handler with mock event
response = handler(test_event, None)

# Print response
print(json.dumps(response, indent=2))