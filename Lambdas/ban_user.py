import json
import boto3
from boto3.dynamodb.conditions import Attr
import os

# Initialize DynamoDB tables from environment variables for best practice
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')

dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table(USERS_TABLE_NAME)
links_table = dynamodb.Table(LINKS_TABLE_NAME)

def _res(status, body):
    """
    Centralized function to create API responses with full CORS headers.
    """
    return {
        "statusCode": status,
        "headers": {
            # Allow requests from any origin
            "Access-Control-Allow-Origin": "*",
            # Allow all standard headers
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            # Allow POST, GET, and the PUT method used by the frontend
            "Access-Control-Allow-Methods": "OPTIONS,POST,PUT,GET"
        },
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    # --- CORS Preflight Handling ---
    # This block handles the browser's initial OPTIONS request.
    if event.get('httpMethod') == 'OPTIONS':
        return {
            "statusCode": 204,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST,PUT,GET"
            },
            "body": ""
        }

    try:
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("UserId")
        active_flag = body.get("IsActive")

        if user_id is None or active_flag is None:
            return _res(400, {"message": "Missing UserId or IsActive field"})

        if not isinstance(active_flag, bool):
            return _res(400, {"message": "IsActive must be a boolean (true or false)"})

        # The active_flag is already a boolean, no need to convert it.
        # DynamoDB's Boto3 library handles boolean types correctly.

        # Update user's IsActive field
        user_table.update_item(
            Key={"UserId": user_id},
            UpdateExpression="SET IsActive = :a",
            ExpressionAttributeValues={":a": active_flag}
        )

        # Update all links owned by this user
        # Note: A Scan operation can be inefficient on large tables.
        # Consider a Global Secondary Index on UserId for better performance.
        links_response = links_table.scan(FilterExpression=Attr("UserId").eq(user_id))
        links = links_response.get("Items", [])
        
        # Handle paginated results from the scan
        while 'LastEvaluatedKey' in links_response:
            links_response = links_table.scan(
                FilterExpression=Attr("UserId").eq(user_id),
                ExclusiveStartKey=links_response['LastEvaluatedKey']
            )
            links.extend(links_response.get("Items", []))


        for link in links:
            link_id = link.get("LinkId")
            if link_id:
                links_table.update_item(
                    Key={"LinkId": link_id},
                    UpdateExpression="SET IsActive = :a",
                    ExpressionAttributeValues={":a": active_flag}
                )

        state = "unbanned" if active_flag else "banned"
        return _res(200, {"message": f"User {user_id} has been {state} and their links have been updated."})

    except Exception as e:
        print(f"Error: {e}")
        return _res(500, {"message": str(e)})

