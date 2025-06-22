import os  # for environment variables
import json  # for JSON parsing and serialization
import boto3  # AWS SDK for Python
import decimal  # to handle DynamoDB Decimal types

# Initialize DynamoDB resource (uses IAM role or AWS credentials)
dynamodb = boto3.resource('dynamodb')
# Table name for Users; override via environment variable (default: 'Users')
TABLE_NAME = os.environ.get('USERS_TABLE', 'Users')


def _decimal_default(obj):
    """
    JSON serializer helper for DynamoDB Decimal objects.
    Converts whole-number Decimals to int, fractional to float.
    """
    if isinstance(obj, decimal.Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def lambda_handler(event, context):
    """
    AWS Lambda entry point: retrieves a user record by UserId.

    Expects JSON body with:
      - UserId (string, required)

    Returns:
      200: {'user': <user item>} on success
      400: {'error': ...} for bad input
      404: {'error': 'User not found'} if no record
      500: {'error': ...} for server errors
    """
    # Parse and validate input
    try:
        raw_body = event.get('body', {})
        # Support string or already-parsed JSON body
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        user_id = body['UserId']
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing or invalid input: {e}'})
        }

    # Reference Users table
    table = dynamodb.Table(TABLE_NAME)
    try:
        # Retrieve item by primary key
        response = table.get_item(Key={'UserId': user_id})
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error fetching user: {e}'})
        }

    # Check if user exists
    user_item = response.get('Item')
    if not user_item:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'User not found'})
        }

    # Return the user record
    return {
        'statusCode': 200,
        'body': json.dumps({'user': user_item}, default=_decimal_default)
    }

# Create a mock event with a valid user ID
# mock_event = {
#     'body': json.dumps({
#         'UserId': 'd4'
#     })
# }

# # Call the lambda handler with the mock event
# response = lambda_handler(mock_event, None)

# # Print the response
# print(json.dumps(response, indent=2))# Create a mock event with a valid user ID

