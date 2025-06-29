import json
import boto3
import os
from botocore.exceptions import ClientError

# --- Initialize DynamoDB ---
dynamodb = boto3.resource('dynamodb')
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
links_table = dynamodb.Table(LINKS_TABLE_NAME)

def _make_response(status_code, body):
    """Creates a CORS-compliant API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            # MODIFIED: Added more allowed methods for future-proofing and robust CORS handling
            'Access-Control-Allow-Methods': 'OPTIONS,POST,PUT,DELETE,GET'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    """
    Removes password protection from a link, with an ownership check.
    """
    # --- CORS Preflight Handling ---
    if event.get('httpMethod') == 'OPTIONS':
        return _make_response(204, {})
        
    try:
        body = json.loads(event.get('body', '{}'))
        link_id = body.get('linkId')
        user_id = body.get('userId') # ID of the user requesting removal

        # --- Input Validation ---
        if not all([link_id, user_id]):
            return _make_response(400, {'message': 'Request must include "linkId" and "userId".'})

    except (json.JSONDecodeError, TypeError):
        return _make_response(400, {'message': 'Invalid JSON format in request body.'})
        
    try:
        # --- Update Item with Ownership Check ---
        # This update does three things:
        # 1. Sets IsPasswordProtected to False.
        # 2. Removes the Password attribute entirely.
        # 3. Ensures this only happens IF the user is the owner AND the link IS currently password protected.
        response = links_table.update_item(
            Key={'LinkId': link_id},
            UpdateExpression="SET IsPasswordProtected = :p_false REMOVE Password",
            ConditionExpression="UserId = :uid AND IsPasswordProtected = :p_true",
            ExpressionAttributeValues={
                ':p_false': False,
                ':uid': user_id,
                ':p_true': True
            },
            ReturnValues="UPDATED_NEW"
        )
        
        return _make_response(200, {'message': 'Password removed successfully.'})

    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            # This error can mean the user is not the owner, or the link wasn't password protected.
            print(f"User '{user_id}' failed to remove password for link '{link_id}'. Check ownership or if password protection was active.")
            return _make_response(409, {'message': 'Conflict: Could not remove password. The link may not be protected or you may not be the owner.'})
        else:
            # Handle other potential database errors
            print(f"DynamoDB Error: {e.response['Error']['Message']}")
            return _make_response(500, {'message': 'A database error occurred.'})

    except Exception as e:
        print(f"Unexpected error: {e}")
        return _make_response(500, {'message': 'An unexpected server error occurred.'})
