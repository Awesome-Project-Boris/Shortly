import os
import json
import string
import secrets
from datetime import datetime
import boto3

# Initialize DynamoDB table from environment variables
TABLE_name = "Links"
DOMAIN = 'https://short.ly'
def lambda_handler(event, context):
    # Parse incoming request body
    try:
        body = json.loads(event.get('body', '{}'))
        long_url = body['url']
    except (json.JSONDecodeError, KeyError):
        return {
            'statusCode': 400,
            'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
            }, 
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
        resp = table.get_item(Key={'linkId': code})
        if 'Item' not in resp:
            break
        code = generate_code()

    # Prepare item to store
    item = {
        'linkId': code,
        'string': long_url,
        'name': name,
        'description': description,
        'isPrivate': is_private,
        'isPasswordProtected': is_password_protected,
        'password': password,
        'numberOfClicks': 0,
        'date': datetime.utcnow().isoformat()
    }

    # Write to DynamoDB
    table.put_item(Item=item)

    # Construct the short URL
    # short_url = f"{DOMAIN}/r/{code}"

    # Return response
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

test_event = {
    'body': json.dumps({
        'url': 'https://www.example.com/url/that/needs/shortening/too',
        'name': 'Example Link',
        'description': 'This is a test link',
        'isPrivate': True,
        'isPasswordProtected': True,
        'password': 'secretpassword123'
    })
}
if __name__ == "__main__":
    print(lambda_handler(test_event, None))