import json
import boto3
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('Users')
notifications_table = dynamodb.Table(os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications'))

def lambda_handler(event, context):
    """
    Checks if a user has any unread notifications.

    Expected request body:
    {
        "UserId": "some-user-id"
    }
    """

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    try:
        # Parse JSON body
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('UserId')

        if not user_id:
            return _res(400, {'message': 'Missing "UserId" in request body.'}, cors_headers)

        # Step 1: Validate user exists
        user_resp = users_table.get_item(Key={"UserId": user_id})
        if 'Item' not in user_resp:
            return _res(404, {'message': f'User {user_id} does not exist.'}, cors_headers)

        # Step 2: Check for unread notifications (IsRead = 0)
        unread_resp = notifications_table.scan(
            FilterExpression=Attr('ToUserId').eq(user_id) & Attr('IsRead').eq(0),
        )

        has_unread = len(unread_resp.get("Items", [])) > 0

        return _res(200, {'hasUnreadNotifications': has_unread}, cors_headers)

    except ClientError as e:
        print(f"DynamoDB ClientError: {e}")
        return _res(500, {'message': 'A database error occurred.'}, cors_headers)

    except Exception as e:
        print(f"Error: {e}")
        return _res(500, {'message': 'An unexpected server error occurred.'}, cors_headers)

def _res(status_code, body_dict, headers):
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body_dict)
    }
