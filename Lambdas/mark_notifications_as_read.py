import json
import boto3
import os
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
NOTIFICATIONS_TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications')

def lambda_handler(event, context):
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,PUT"
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

        # Step 1: Query for unread notifications
        response = table.query(
            IndexName='ToUserId-index',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('ToUserId').eq(user_id)
        )
        notifications = response.get('Items', [])

        # Step 2: Update each unread notification
        for notification in notifications:
            if not notification.get('IsRead'):
                table.update_item(
                    Key={'NotifId': notification['NotifId']},
                    UpdateExpression='SET IsRead = :r',
                    ExpressionAttributeValues={':r': 1}
                )

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
