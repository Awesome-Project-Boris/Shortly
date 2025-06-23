import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
# Use an environment variable for the table name
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')

def lambda_handler(event, context):
    """
    Verifies the password for a protected link.
    
    Expects a JSON body with:
    - linkId (string): The ID of the link to verify.
    - password (string): The password submitted by the user.
    """
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    try:
        body = json.loads(event.get('body', '{}'))
        link_id = body.get('linkId')
        submitted_password = body.get('password')

        if not link_id or not submitted_password:
            return {'statusCode': 400, 'headers': cors_headers, 'body': json.dumps({'message': 'LinkId and password are required.'})}

        table = dynamodb.Table(LINKS_TABLE_NAME)

        # --- Get the link from DynamoDB ---
        response = table.get_item(Key={'LinkId': link_id})
        
        if 'Item' not in response:
            return {'statusCode': 404, 'headers': cors_headers, 'body': json.dumps({'message': 'Link not found.'})}
        
        link_item = response['Item']

        # --- Verify the link is actually password protected ---
        if not link_item.get('IsPasswordProtected'):
            # Even if the link isn't protected, if the request was made, we grant access.
            return {'statusCode': 200, 'headers': cors_headers, 'body': json.dumps({'accessGranted': True, 'originalUrl': link_item.get('String')})}
        
        # --- Verify Password ---
        # SECURITY NOTE: This assumes plaintext passwords. For production, use a hashing library like bcrypt.
        stored_password = link_item.get('Password')
        
        if stored_password == submitted_password:
            # Success! Password matches.
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'accessGranted': True,
                    'originalUrl': link_item.get('String')
                })
            }
        else:
            # Failure. Password does not match.
            return {
                'statusCode': 200, # Still a valid request, just access is denied.
                'headers': cors_headers,
                'body': json.dumps({
                    'accessGranted': False,
                    'message': 'Incorrect password. Please try again.'
                })
            }

    except ClientError as e:
        print(f"DynamoDB Error: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'A database error occurred.'})}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'An unexpected server error occurred.'})}
