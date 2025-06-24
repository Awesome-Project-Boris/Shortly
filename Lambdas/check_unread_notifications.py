import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Get the Users table name from environment variables for best practice
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')

def lambda_handler(event, context):
    """
    Checks if a user is active or banned.
    This function now explicitly handles OPTIONS pre-flight requests for robust CORS support.
    
    Expects a JSON body with:
    - userId (string): The ID of the user to check.
    """
    
    # Define a comprehensive set of CORS headers. These will be included in every response.
    # This allows any domain (*) to call your API and specifies the allowed methods and headers.
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }
    
    # --- NEW: Handle OPTIONS pre-flight request ---
    # The browser sends this automatically before the actual POST request.
    # We must respond with a 200 OK and the correct headers.
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'CORS pre-flight check successful.'})
        }

    try:
        # Get the userId from the request body
        body = json.loads(event.get('body', '{}'))
        user_id_to_check = body.get('userId')

        if not user_id_to_check:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'userId is required in the request body.'})
            }

        table = dynamodb.Table(USERS_TABLE_NAME)
        
        # --- Fetch only the 'IsActive' attribute for efficiency ---
        response = table.get_item(
            Key={'UserId': user_id_to_check},
            ProjectionExpression='IsActive'
        )
        
        user_item = response.get('Item')

        is_active_status = False
        if user_item:
            # If the user exists, get their status.
            # Default to True if the 'IsActive' attribute is missing for some reason.
            is_active_status = user_item.get('IsActive', True)
        else:
            # If the user is not found in the database, they cannot be considered active.
            print(f"User with ID {user_id_to_check} not found. Returning inactive.")
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            # Return a direct JSON object that the front-end can easily use
            'body': json.dumps({'isActive': is_active_status})
        }

    except ClientError as e:
        print(f"DynamoDB ClientError: {e.response['Error']['Message']}")
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
