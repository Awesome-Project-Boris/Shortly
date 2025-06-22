import os  # Operate system environment variables
import json  # Parse and serialize JSON payloads
import boto3  # AWS SDK for Python (Boto3)
import decimal  # Handle DynamoDB numeric Decimal types

# --- Initialize AWS resources ---
# DynamoDB resource uses IAM role or env credentials
dynamodb = boto3.resource('dynamodb')
# Table name for Users; can be overridden via Lambda environment variables
TABLE_NAME = os.environ.get('USERS_TABLE', 'Users')


def _decimal_default(obj):
    """
    JSON serializer helper for DynamoDB Decimal objects.
    Converts whole-number Decimal to int, fractional to float.
    """
    if isinstance(obj, decimal.Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def lambda_handler(event, context):
    """
    AWS Lambda entry point: fetches detailed friends info for a user.

    Steps:
      1. Parse 'UserId' from request body.
      2. Retrieve the user's 'Friends' list of UserIds.
      3. For each friend UserId, fetch their record and extract UserId,
         Username, Picture, and Email.
      4. Return a JSON array of friend summaries.
    """
    # --- 1. Parse and validate input parameters ---
    try:
        raw_body = event.get('body', {})
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        user_id = body['UserId']  # required
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing or invalid input: {e}'})
        }

    # Table reference
    table = dynamodb.Table(TABLE_NAME)

    # --- 2. Fetch user record and extract friends list ---
    try:
        response = table.get_item(Key={'UserId': user_id})
        user_item = response.get('Item')
        if not user_item:
            return {'statusCode': 404, 'body': json.dumps({'error': 'User not found'})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': f'Error fetching user: {e}'})}

    # Parse raw JSON or list from 'Friends' attribute
    friends_attr = user_item.get('Friends', '[]')
    if isinstance(friends_attr, str):
        try:
            friends_ids = json.loads(friends_attr)
        except json.JSONDecodeError:
            friends_ids = []  # fallback on parse error
    else:
        friends_ids = friends_attr

    # --- 3. Fetch each friend's details ---
    friends_info = []
    for fid in friends_ids:
        try:
            fr = table.get_item(Key={'UserId': fid}).get('Item')
            if fr:
                # Extract only desired fields
                friends_info.append({
                    'UserId': fr.get('UserId', ''),
                    'Username': fr.get('Username', ''),
                    'Picture': fr.get('Picture', ''),
                    'Email': fr.get('Email', '')
                })
        except Exception:
            # Skip any friend lookup errors silently
            continue

    # --- 4. Return list of friend summaries ---
    return {
        'statusCode': 200,
        'body': json.dumps({'friends': friends_info}, default=_decimal_default)
    }


# Create a mock event with a valid user ID
# mock_event = {
#     'body': json.dumps({
#         'UserId': 'Allie1'
#     })
# }

# # Call the lambda handler with the mock event
# response = lambda_handler(mock_event, None)

# # Print the response
# print(json.dumps(response, indent=2))