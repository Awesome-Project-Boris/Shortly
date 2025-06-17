import json
import boto3
import os
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Fetch table name from environment variables
NOTIFICATIONS_TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications')

def lambda_handler(event, context):
    """
    Fetches all relevant notifications for a user, separated into two categories:
    1. Pending friend requests.
    2. Other notifications (e.g., achievements) from the last 7 days.
    
    Expects a userId in the query string parameters.
    e.g., /notifications/all?userId=some-user-id
    """
    
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,GET"
    }

    try:
        params = event.get('queryStringParameters', {})
        user_id = params.get('userId')

        if not user_id:
            return {'statusCode': 400, 'headers': cors_headers, 'body': json.dumps({'message': 'Missing "userId" in query parameters.'})}

        table = dynamodb.Table(NOTIFICATIONS_TABLE_NAME)
        
        # --- Query 1: Get Pending Friend Requests ---
        # A friend request is identified by having a 'Status' attribute set to 'pending'.
        friend_requests_response = table.query(
            IndexName='ToUserId-index',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('ToUserId').eq(user_id),
            FilterExpression=boto3.dynamodb.conditions.Attr('Status').eq('pending')
        )
        friend_requests = friend_requests_response.get('Items', [])

        # --- Query 2: Get Other Notifications from the last 7 days ---
        # Other notifications are identified by NOT having a 'Status' attribute.
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        seven_days_ago_iso = seven_days_ago.isoformat()

        other_notifications_response = table.query(
            IndexName='ToUserId-index',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('ToUserId').eq(user_id),
            # Filter for items where 'Status' does not exist AND 'Timestamp' is recent.
            FilterExpression=boto3.dynamodb.conditions.Attr('Status').not_exists() & boto3.dynamodb.conditions.Attr('Timestamp').gt(seven_days_ago_iso)
        )
        other_notifications = other_notifications_response.get('Items', [])
        
        # --- Combine results into a single response object ---
        response_body = {
            'friendRequests': friend_requests,
            'otherNotifications': other_notifications
        }

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(response_body)
        }

    except ClientError as e:
        print(f"DynamoDB ClientError: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'A database error occurred.'})}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'An unexpected server error occurred.'})}

