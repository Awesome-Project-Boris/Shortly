import os
import json
import uuid
from datetime import datetime, timezone
import boto3

dynamodb = boto3.resource('dynamodb')
# Table name should be set as an environment variable
TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE', 'Notifications')

def lambda_handler(event, context):
    """
    AWS Lambda handler to "send" a notification by saving it into DynamoDB.

    Expected JSON body with keys:
      - FromUserID (string, optional)
      - ToUserID (string, required)
      - Status (string, optional; e.g., "pending", "accepted", "rejected")
      - IsRead (int; 0 or 1)
      - Text (string, required)
      - LinkId (string, optional)
      - Timestamp (ISO 8601 string, optional)
    """
    # Parse and validate input
    try:
        body = event.get('body')
        if isinstance(body, str):
            body = json.loads(body)

        # Required fields
        to_user = body['ToUserId']
        text = body['Text']
        is_read = int(body.get('IsRead', 0))

        # Optional fields
        from_user = body.get('FromUserId', '')
        status = body.get('Status', 'pending')
        link_id = body.get('LinkId', '')
        timestamp = body.get('Timestamp', datetime.now(timezone.utc).isoformat())
    except (KeyError, ValueError, TypeError) as e:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing or invalid input: {str(e)}'})
            }

    # Generate defaults
    notification_id = str(uuid.uuid4())

    # Prepare item
    item = {
        'NotificationId': notification_id,
        'FromUserId': from_user,
        'ToUserId': to_user,
        'Status': status,
        'IsRead': is_read,
        'Text': text,
        'LinkId': link_id,
        'Timestamp': timestamp
    }

    # Save to DynamoDB
    table = dynamodb.Table(TABLE_NAME)
    try:
        table.put_item(Item=item)
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to save notification: {str(e)}'})
        }

    # Return response
    return {
        'statusCode': 201,
        'body': json.dumps({'message': 'Notification queued', 'NotificationID': notification_id})
    }
# Create mock event with test notification data
# test_event = {
#     'body': json.dumps({
#         'FromUserId': 'user123',
#         'ToUserId': 'user456', 
#         'Status': 'pending',
#         'IsRead': 0,
#         'Text': 'This is a test notification',
#         'LinkId': 'link789',
        
#     })
# }

# # Call lambda handler with test event
# result = lambda_handler(test_event, None)
# print(result)