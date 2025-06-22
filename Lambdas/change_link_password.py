import json
import boto3
from botocore.exceptions import ClientError
# It's highly recommended to use a secure hashing library for passwords.
# import bcrypt

# Initialize the DynamoDB resource
dynamodb = boto3.resource('dynamodb')
LINKS_TABLE = 'Links' # Replace with your actual table name

def lambda_handler(event, context):
    """
    Updates the password for a specific link after verifying ownership and the current password.
    
    Expects a JSON body with:
    - linkId (string): The ID of the link to update.
    - userId (string): The ID of the user making the request (to verify ownership).
    - currentPassword (string): The existing password for the link.
    - newPassword (string): The new password to set.
    """
    
    # Define CORS headers to be included in every response.
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,PUT,POST"
    }

    try:
        # Load the request body from the event
        body = json.loads(event.get('body', '{}'))
        
        link_id = body.get('linkId')
        user_id = body.get('userId')
        current_password = body.get('currentPassword')
        new_password = body.get('newPassword')

        # --- Input Validation ---
        if not all([link_id, user_id, current_password, new_password]):
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({"message": "Missing required fields in the request body (linkId, userId, currentPassword, newPassword)."})
            }

        table = dynamodb.Table(LINKS_TABLE)

        # --- Step 1: Get the link from DynamoDB ---
        response = table.get_item(Key={'LinkId': link_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({"message": f"Link with ID '{link_id}' not found."})
            }
        
        link_item = response['Item']

        # --- Step 2: Verify Ownership ---
        # DEVELOPER NOTE: This assumes you have an 'ownerId' attribute on your 'Links' table
        # that stores the userID of the user who created the link. This is critical for security.
        if link_item.get('ownerId') != user_id:
            return {
                'statusCode': 403, # Forbidden
                'headers': cors_headers,
                'body': json.dumps({"message": "Forbidden. You do not have permission to modify this link."})
            }
            
        # --- Step 3: Verify the Link is Password Protected ---
        if not link_item.get('IsPasswordProtected'):
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({"message": "This link is not password protected."})
            }

        # --- Step 4: Verify the Current Password ---
        # SECURITY BEST PRACTICE: Passwords should be stored as hashes.
        # The comparison would look like:
        # stored_hash = link_item.get('Password').encode('utf-8')
        # if not bcrypt.checkpw(current_password.encode('utf-8'), stored_hash):
        #
        # For this example, we'll use a direct string comparison as implied by the current setup.
        if link_item.get('Password') != current_password:
            return {
                'statusCode': 401, # Unauthorized
                'headers': cors_headers,
                'body': json.dumps({"message": "Incorrect current password."})
            }

        # --- Step 5: Update the Password ---
        # SECURITY BEST PRACTICE: The new password should be hashed before saving.
        # new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        table.update_item(
            Key={'LinkId': link_id},
            UpdateExpression='SET #pwd = :new_password',
            # Using ExpressionAttributeNames because 'Password' can be a reserved word in DynamoDB
            ExpressionAttributeNames={'#pwd': 'Password'},
            ExpressionAttributeValues={':new_password': new_password}
        )

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({"message": "Password updated successfully."})
        }

    except ClientError as e:
        print(f"DynamoDB ClientError: {e.response['Error']['Message']}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({"message": "A database error occurred."})
        }
            
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({"message": "Invalid JSON format in request body."})
        }

    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({"message": "An unexpected server error occurred."})
        }
