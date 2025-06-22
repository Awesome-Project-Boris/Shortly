import json
import boto3
from botocore.exceptions import ClientError

# Initialize the DynamoDB resource
dynamodb = boto3.resource('dynamodb')
LINKS_TABLE = 'Links'

def lambda_handler(event, context):
    """
    Toggles the 'IsPrivate' boolean attribute for a given link.
    Expects a JSON body with 'linkId' (string).
    """
    
    # Define CORS headers for the response
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    try:
        # Load the request body to get the linkId
        body = json.loads(event.get('body', '{}'))
        link_id = body.get('linkId')

        # --- Input Validation ---
        if not link_id or not isinstance(link_id, str):
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({"message": "Request body must contain a valid 'linkId'."})
            }

        table = dynamodb.Table(LINKS_TABLE)

        # --- Step 1: Get the current item to read its state ---
        response = table.get_item(Key={'LinkId': link_id})

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({"message": f"Link with ID '{link_id}' not found."})
            }
        
        # Get the current status. Default to False if the attribute doesn't exist for some reason.
        current_status = response['Item'].get('IsPrivate', False)

        # --- Step 2: "Flip" the boolean value ---
        new_status = not current_status
        
        # --- Step 3: Update the item with the new value ---
        table.update_item(
            Key={'LinkId': link_id},
            UpdateExpression='SET IsPrivate = :new_status',
            ExpressionAttributeValues={
                ':new_status': new_status
            }
        )
        
        # Return a success message with the new flipped state
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                "message": "Link privacy toggled successfully.",
                "newIsPrivateState": new_status
            })
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