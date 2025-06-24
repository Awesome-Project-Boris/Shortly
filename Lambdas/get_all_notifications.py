import json
import boto3
import os
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Fetch table name from environment variables
NOTIFICATIONS_TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications')
# It's also good practice to make the index name an environment variable
USER_ID_INDEX_NAME = os.environ.get('USER_ID_INDEX_NAME', 'ToUserId-index')

def lambda_handler(event, context):
    """
    Fetches all relevant notifications for a user, separated into two categories:
    1. Pending friend requests.
    2. Other notifications (e.g., achievements) from the last 7 days.
    """
    
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST" 
    }

    # Handle CORS pre-flight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'CORS pre-flight check successful.'})
        }

    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId')

        if not user_id:
            return {'statusCode': 400, 'headers': cors_headers, 'body': json.dumps({'message': 'Missing "userId" in request body.'})}

        table = dynamodb.Table(NOTIFICATIONS_TABLE_NAME)
        
        # --- Query 1: Get Pending Friend Requests ---
        friend_requests_response = table.query(
            IndexName=USER_ID_INDEX_NAME,
            KeyConditionExpression=boto3.dynamodb.conditions.Key('ToUserId').eq(user_id),
            FilterExpression=boto3.dynamodb.conditions.Attr('Status').eq('pending')
        )
        friend_requests = friend_requests_response.get('Items', [])

        # --- Query 2: Get Other Notifications from the last 7 days ---
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        seven_days_ago_iso = seven_days_ago.isoformat()

        other_notifications_response = table.query(
            IndexName=USER_ID_INDEX_NAME,
            KeyConditionExpression=boto3.dynamodb.conditions.Key('ToUserId').eq(user_id),
            FilterExpression=boto3.dynamodb.conditions.Attr('Status').not_exists() & boto3.dynamodb.conditions.Attr('Timestamp').gt(seven_days_ago_iso)
        )
        other_notifications = other_notifications_response.get('Items', [])
        
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
        # NEW: Specific check for a missing index
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            error_msg = f"DynamoDB Index '{USER_ID_INDEX_NAME}' not found. Please create the GSI on the '{NOTIFICATIONS_TABLE_NAME}' table."
            print(f"ERROR: {error_msg}")
            return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'Server configuration error.'})}
        
        print(f"DynamoDB ClientError: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'A database error occurred.'})}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'An unexpected server error occurred.'})}

