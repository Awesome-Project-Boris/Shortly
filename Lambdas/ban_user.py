import json
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table("Users")
links_table = dynamodb.Table("Links")  # Assumes "Links" table exists

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("UserId")
        active_flag = body.get("IsActive")

        if user_id is None or active_flag is None:
            return _res(400, "Missing UserId or IsActive field")

        if not isinstance(active_flag, bool):
            return _res(400, "isActive must be a boolean (true or false)")

        # Convert to string as required by the schema
        is_active_str = "true" if active_flag else "false"

        # Update user's IsActive field
        user_table.update_item(
            Key={"UserId": user_id},
            UpdateExpression="SET IsActive = :a",
            ExpressionAttributeValues={":a": is_active_str}
        )

        # Update all links owned by this user
        links = links_table.scan(FilterExpression=Attr("UserId").eq(user_id)).get("Items", [])

        for link in links:
            link_id = link.get("LinkId")
            if link_id:
                links_table.update_item(
                    Key={"LinkId": link_id},
                    UpdateExpression="SET IsActive = :a",
                    ExpressionAttributeValues={":a": is_active_str}
                )

        state = "activated" if active_flag else "banned"
        return _res(200, f"User {user_id} has been {state} and their links {state}.")

    except Exception as e:
        return _res(500, str(e))


def _res(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message})
    }
