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
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    """
    Sets a password for a link that doesn't have one, with an ownership check.
    """
    # --- CORS Preflight Handling ---
    if event.get('httpMethod') == 'OPTIONS':
        return _make_response(204, {})
        
    try:
        body = json.loads(event.get('body', '{}'))
        link_id = body.get('linkId')
        user_id = body.get('userId')
        new_password = body.get('newPassword')

        # --- Input Validation ---
        if not all([link_id, user_id, new_password]):
            return _make_response(400, {'message': 'Request must include "linkId", "userId", and "newPassword".'})
        
        if len(new_password) < 4:
            return _make_response(400, {'message': 'Password must be at least 4 characters long.'})

    except (json.JSONDecodeError, TypeError):
        return _make_response(400, {'message': 'Invalid JSON format in request body.'})
        
    try:
        # --- Update Item with Ownership and State Check ---
        # This update does three things at once:
        # 1. Sets IsPasswordProtected to True.
        # 2. Sets the new Password.
        # 3. Ensures this only happens IF the user is the owner AND the link is NOT already password protected.
        response = links_table.update_item(
            Key={'LinkId': link_id},
            UpdateExpression="SET IsPasswordProtected = :p_true, Password = :pass",
            ConditionExpression="UserId = :uid AND (attribute_not_exists(IsPasswordProtected) OR IsPasswordProtected = :p_false)",
            ExpressionAttributeValues={
                ':p_true': True,
                ':pass': new_password,
                ':uid': user_id,
                ':p_false': False
            },
            ReturnValues="UPDATED_NEW"
        )
        
        return _make_response(200, {'message': 'Password set successfully.'})

    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            # This error can mean one of two things: either the user is not the owner,
            # or the link already has a password.
            print(f"User '{user_id}' failed to set password for link '{link_id}'. Check ownership or if password already exists.")
            return _make_response(409, {'message': 'Conflict: Could not set password. The link may already be protected or you may not be the owner.'})
        else:
            # Handle other potential database errors
            print(f"DynamoDB Error: {e.response['Error']['Message']}")
            return _make_response(500, {'message': 'A database error occurred.'})

    except Exception as e:
        print(f"Unexpected error: {e}")
        return _make_response(500, {'message': 'An unexpected server error occurred.'})

# Create a mock event with valid data
# mock_event = {
#     "httpMethod": "POST",
#     "body": json.dumps({
#         "linkId": "test-link-123",
#         "userId": "test-user-456",
#         "newPassword": "test-password"
#     })
# }

# # Call the lambda handler with mock event
# response = lambda_handler(mock_event, None)