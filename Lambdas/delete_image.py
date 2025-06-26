import json
import os
import boto3
from botocore.exceptions import ClientError

# --- Initialize AWS Clients ---
dynamodb = boto3.resource('dynamodb')

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')
users_table = dynamodb.Table(USERS_TABLE_NAME)

def _make_response(status_code, body):
    """
    Centralized function to create API responses with full CORS headers.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    """
    Reverts a user's profile picture to a default image in DynamoDB.
    This function no longer deletes objects from S3.
    It now accepts a 'pictureUrl' in the body.
    """
    # --- CORS Preflight Handling ---
    if event.get('httpMethod') == 'OPTIONS':
        return _make_response(204, {})

    try:
        # Load the userId and optional pictureUrl from the request body
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId')
        picture_url = body.get('pictureUrl')

        if not user_id:
            return _make_response(400, {'message': 'Request must include "userId".'})

        # Use the provided pictureUrl, or a fallback placeholder if it's not provided.
        final_picture_url = picture_url if picture_url else "https://placehold.co/150x150/6c757d/FFFFFF?text=Avatar"

        # --- Perform the DynamoDB Update ---
        print(f"Attempting to reset picture for user: {user_id} to URL: {final_picture_url}")
        users_table.update_item(
            Key={'UserId': user_id},
            UpdateExpression="SET Picture = :p",
            ExpressionAttributeValues={':p': final_picture_url},
            ConditionExpression="attribute_exists(UserId)" # Ensure the user exists
        )

        return _make_response(200, {'message': 'Profile picture reset successfully.'})

    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            return _make_response(404, {'message': f"User with ID '{user_id}' not found."})
        print(f"DynamoDB Error: {e.response['Error']['Message']}")
        return _make_response(500, {'message': 'A database error occurred.'})
    
    except (json.JSONDecodeError, TypeError):
        return _make_response(400, {'message': 'Invalid JSON format in request body.'})

    except Exception as e:
        print(f"Error: {e}")
        return _make_response(500, {'message': 'An unexpected server error occurred.'})
