import os
import json
import boto3
from datetime import datetime

table_name = "LinkClicksByUser"
link_table_name = "Links"


dynamodb = boto3.resource('dynamodb')
analytics_table = dynamodb.Table(table_name)
link_table = dynamodb.Table(link_table_name)


def lambda_handler(event, context):
    # Extract short code from path parameters
    code = event.get('pathParameters', {}).get('code')
    if not code:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing code parameter.'})
        }

    # Parse optional userID from query string (no authorizer)
    params = event.get('queryStringParameters') or {}
    user_id = params.get('userID')
    if not user_id:
        # Track anonymous clicks separately or return error
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'userID query parameter is required'})
        }

    # Fetch original link
    resp = link_table.get_item(Key={'linkID': code})
    item = resp.get('Item')
    if not item:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Link not found.'})
        }

    # Update per-user click count
    analytics_table.update_item(
        Key={
            'linkID': code,
            'userID': user_id
        },
        UpdateExpression='ADD ClickCount :inc',
        ExpressionAttributeValues={
            ':inc': 1
        }
    )

    # Optionally increment overall click count
    link_table.update_item(
        Key={'linkID': code},
        UpdateExpression='ADD NumberOfClicks :inc',
        ExpressionAttributeValues={
            ':inc': 1
        }
    )

    # Redirect to the original URL
    return {
        'statusCode': 301,
        'headers': {
            'Location': item['String']
        }
    }

def create_test_event():
    return {
        'pathParameters': {
            'code': 'J6GbhU6w'
        },
        'queryStringParameters': {
            'userID': '456'
        }
    }
    
if __name__ == "__main__":
    print(lambda_handler(create_test_event(), None))