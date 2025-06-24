import os
import json
import string
import secrets
from datetime import datetime
import boto3

# Initialize DynamoDB table from environment variables
TABLE_NAME = 'Links'


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)


def generate_code(length: int = 8) -> str:
    """
    Generate a random base62 string for the short code.
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def lambda_handler(event, context):
    # Parse incoming request body
    try:
        body = json.loads(event.get('body', '{}'))
        long_url = body['url']
        user_id = body['userId']
    except (json.JSONDecodeError, KeyError):
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'error': 'Request must be JSON with "url" and "userId" fields.'})
        }

    # Extract optional fields with defaults
    name = body.get('name', '')
    description = body.get('description', '')
    is_private = bool(body.get('isPrivate', False))
    is_password_protected = bool(body.get('isPasswordProtected', False))
    password = body.get('password', '')

    # Validate password protection logic
    if is_password_protected and not password:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'error': 'Password must be provided when isPasswordProtected is true.'})
        }
    if not is_password_protected:
        password = ''  # enforce empty password when protection is off

    # Generate a unique short code, retrying on collisions
    code = generate_code()
    while True:
        resp = table.get_item(Key={'LinkId': code})
        if 'Item' not in resp:
            break
        code = generate_code()

    # Prepare item to store, now including UserId
    item = {
        'LinkId': code,
        'UserId': user_id,
        'String': long_url,
        'Name': name,
        'Description': description,
        'IsPrivate': is_private,
        'IsPasswordProtected': is_password_protected,
        'Password': password,
        'NumberOfClicks': 0,
        'Date': datetime.utcnow().isoformat(),
        'IsActive': True
    }

    # Write to DynamoDB
    table.put_item(Item=item)

    # Return response with the new code
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'code': code})
    }

# Example test event
# if __name__ == "__main__":
#     test_event = {
#         'body': json.dumps({
#             'url': 'https://www.public.com/url/that/needs/shortening/too/3',
#             'userId': 'Bobby Jr.2',
#             'name': 'Admin Page Test Link',
#             'description': 'This is a test link',
#             'isPrivate': True,
#             'isPasswordProtected': True,
#             'password': 'secretpassword123'
#         })
#     }
#     print(lambda_handler(test_event, None))