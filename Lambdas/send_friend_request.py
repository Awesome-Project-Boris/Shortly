import json
import boto3
import uuid
from datetime import datetime
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table("Users")
notification_table = dynamodb.Table("Notifications")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        from_user = body["FromUserId"]
        to_user = body["ToUserId"]

        if from_user == to_user:
            return _res(400, "Cannot send request to yourself.")

        # Check both users exist
        from_data = users_table.get_item(Key={"UserId": from_user}).get("Item")
        to_data = users_table.get_item(Key={"UserId": to_user}).get("Item")
        if not from_data or not to_data:
            return _res(404, "User not found.")

        # Look for existing friend requests between these users (any direction)
        existing = notification_table.scan(
            FilterExpression=(
                (Attr("FromUserId").eq(from_user) & Attr("ToUserId").eq(to_user)) |
                (Attr("FromUserId").eq(to_user) & Attr("ToUserId").eq(from_user))
            )
        )

        for req in existing.get("Items", []):
            status = req.get("Status")
            sender = req.get("FromUserId")
            receiver = req.get("ToUserId")

            if status == "pending":
                return _res(400, "A friend request is already pending between these users.")

            if status == "accepted":
                return _res(400, "You are already friends.")

            if status == "rejected":
                if sender == from_user:
                    return _res(400, "Your previous request was rejected. Let the other user send a request.")

        # No conflict, create friend request notification
        notif_id = str(uuid.uuid4())
        text = f"{from_data.get('FullName', 'Someone')} wants to be friends."

        item = {
            "NotificationId": notif_id,
            "FromUserId": from_user,
            "ToUserId": to_user,
            "Status": "pending",
            "IsRead": 0,
            "Text": text,
            "LinkId": "",
            "Timestamp": datetime.utcnow().isoformat()
        }
        
        # Example Request Body
        # {
        #     "FromUserId": "user123",
        #     "ToUserId": "user456"
        # }
        
        notification_table.put_item(Item=item)
        return _res(200, "Friend request sent.")

    except Exception as e:
        return _res(500, str(e))


def _res(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message})
    }
