import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Fetch table name from environment variables
NOTIFICATIONS_TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications')

def lambda_handler(event, context):
    """
    Finds all unread notifications for a given user and marks them as read.

    Expects a userId in the POST request body.
    e.g., POST /notifications/markread with body {"userId": "some-user-id"}
    """
    
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId')

        if not user_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Missing "userId" in request body.'})
            }

        table = dynamodb.Table(NOTIFICATIONS_TABLE_NAME)

        # --- Step 1: Find all notifications for the user ---
        # NOTE: This requires the 'ToUserId-index' GSI mentioned previously.
        response = table.query(
            IndexName='ToUserId-index',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('ToUserId').eq(user_id)
        )
        
        notifications_to_update = response.get('Items', [])
        
        # --- Step 2: Update them in a batch ---
        # The batch_writer is a high-level tool that handles batching, retries, etc.
        # It's the most efficient way to update multiple items.
        if notifications_to_update:
            with table.batch_writer() as batch:
                for notification in notifications_to_update:
                    # We only update items that are currently unread.
                    if not notification.get('IsRead'):
                        batch.update_item(
                            Key={'NotificationId': notification['NotificationId']},
                            UpdateExpression='SET IsRead = :is_read',
                            ExpressionAttributeValues={':is_read': True}
                        )
            print(f"Marked notifications as read for user: {user_id}")

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Notifications marked as read.'})
        }

    except ClientError as e:
        print(f"DynamoDB ClientError: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'A database error occurred.'})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'An unexpected server error occurred.'})
        }
