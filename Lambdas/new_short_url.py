import os
import json
import string
import secrets
from datetime import datetime
import boto3

# Initialize DynamoDB table from environment variables
TABLE_NAME = os.environ['LINKS_TABLE']
DOMAIN = os.environ.get('URL_DOMAIN', 'https://short.ly')

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
    except (json.JSONDecodeError, KeyError):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Request must be JSON with a "url" field.'})
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

    # Prepare item to store
    item = {
        'LinkId': code,
        'String': long_url,
        'Name': name,
        'Description': description,
        'IsPrivate': is_private,
        'IsPasswordProtected': is_password_protected,
        'Password': password,
        'NumberOfClicks': 0,
        'Date': datetime.utcnow().isoformat()
    }

    # Write to DynamoDB
    table.put_item(Item=item)

    # Construct the short URL
    short_url = f"{DOMAIN}/r/{code}"

    # Return response
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'shortUrl': short_url})
    }
```
