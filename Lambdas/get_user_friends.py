import os
import json
import boto3
import decimal

# --- Initialize AWS resources ---
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('USERS_TABLE', 'Users')

# --- CORS Headers ---
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'OPTIONS,POST'
}

def _decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def lambda_handler(event, context):
    # Handle preflight OPTIONS request
    if event.get("httpMethod") == "OPTIONS":
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'CORS preflight success'})
        }

    try:
        raw_body = event.get('body', {})
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        user_id = body['UserId']
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Missing or invalid input: {e}'})
        }

    table = dynamodb.Table(TABLE_NAME)

    try:
        response = table.get_item(Key={'UserId': user_id})
        user_item = response.get('Item')
        if not user_item:
            return {
                'statusCode': 404,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'User not found'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Error fetching user: {e}'})
        }

    friends_attr = user_item.get('Friends', '[]')
    if isinstance(friends_attr, str):
        try:
            friends_ids = json.loads(friends_attr)
        except json.JSONDecodeError:
            friends_ids = []
    else:
        friends_ids = friends_attr

    friends_info = []
    for fid in friends_ids:
        try:
            fr = table.get_item(Key={'UserId': fid}).get('Item')
            if fr:
                friends_info.append({
                    'UserId': fr.get('UserId', ''),
                    'Username': fr.get('Username', ''),
                    'Picture': fr.get('Picture', ''),
                    'Email': fr.get('Email', '')
                })
        except Exception:
            continue

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({'friends': friends_info}, default=_decimal_default)
    }
