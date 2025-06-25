import json
import os

def lambda_handler(event, context):
    """
    Checks if a given UserId matches the site's administrator ID.
    The admin ID is stored securely as an environment variable.
    
    Expects a JSON body with:
    - UserId (string): The ID of the user to check.
    """
    body = json.loads(event.get('body', '{}'))
    ADMIN_USER_ID = body.get('UserId')
    
    cors_headers =  {"Content-Type": "application/json",
                    'Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                    'Access-Control-Allow-Origin': "*"
                    }

    if not ADMIN_USER_ID:
        print("CRITICAL: ADMIN_USER_ID environment variable is not set.")
        # Return a server error because the function is not configured correctly.
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Server configuration error.'})
        }
        
    try:
        body = json.loads(event.get('body', '{}'))
        user_id_to_check = body.get('UserId')

        if not user_id_to_check:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'UserId is required in the request body.'})
            }

        # --- Verification Logic ---
        is_admin = (user_id_to_check == ADMIN_USER_ID)
        
        print(f"Checked user {user_id_to_check}. Is admin: {is_admin}")

        return {
            'statusCode': 200,
            'headers': cors_headers,
            # Return a simple, direct JSON response
            'body': json.dumps({'IsAdmin': is_admin})
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'An unexpected server error occurred.'})
        }
