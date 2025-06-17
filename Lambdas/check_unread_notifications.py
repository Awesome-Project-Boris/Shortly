import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Fetch table name from environment variables for best practice
NOTIFICATIONS_TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications')

def lambda_handler(event, context):
    """
    Checks if a user has any notifications where 'IsRead' is False.
    This function is optimized to stop at the first unread notification found.

    Expects a userId in the query string parameters.
    e.g., /notifications/unread?userId=some-user-id
    """
    
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,GET"
    }

    try:
        # Get userId from the query string
        params = event.get('queryStringParameters', {})
        user_id = params.get('userId')

        if not user_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Missing "userId" in query string parameters.'})
            }

        table = dynamodb.Table(NOTIFICATIONS_TABLE_NAME)

        # --- Efficient DynamoDB Query ---
        # NOTE: For this query to be efficient, you MUST have a Global Secondary Index (GSI)
        # on your Notifications table with 'ToUserId' as the partition key.
        # Let's assume the GSI is named 'ToUserIdIndex'.
        
        response = table.query(
            IndexName='ToUserId-index',  # Name of your GSI
            # Query for items where ToUserId matches the provided user_id
            KeyConditionExpression=boto3.dynamodb.conditions.Key('ToUserId').eq(user_id),
            # Filter the results of the query to only include items where IsRead is False
            FilterExpression=boto3.dynamodb.conditions.Attr('IsRead').eq(False),
            # We only need to know if one exists, so we limit the result to 1.
            # This is highly efficient and cost-effective.
            Limit=1 
        )

        # If the 'Items' list has anything in it, it means we found at least one unread notification.
        has_unread = len(response.get('Items', [])) > 0

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'hasUnreadNotifications': has_unread})
        }

    except ClientError as e:
        # This can happen if the GSI doesn't exist or there's a permission issue.
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
             print("ERROR: GSI 'ToUserId-index' not found on Notifications table.")
        
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
