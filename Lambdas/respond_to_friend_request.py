import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from uuid import uuid4
from decimal import Decimal

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')
notif_table = dynamodb.Table("Notifications")
user_table = dynamodb.Table("Users")

# CORS headers
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    "Access-Control-Allow-Origin": "*"
}

def _decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return _res(200, {"message": "CORS preflight OK"})

    try:
        body = json.loads(event.get("body", "{}"))
        notification_id = body.get("NotifId") or body.get("notificationID")
        accept = bool(body.get("accept", False))

        if not notification_id:
            return _res(400, "Missing NotifId.")

        # Get the original friend request
        notif_resp = notif_table.get_item(Key={"NotifId": notification_id})
        notif = notif_resp.get("Item")
        if not notif or notif.get("Status") != "pending":
            return _res(404, "Pending friend request not found.")

        from_user = notif["FromUserId"]
        to_user = notif["ToUserId"]

        # Mark original request as read and update status
        notif_table.update_item(
            Key={"NotifId": notification_id},
            UpdateExpression="SET #s = :s, IsRead = :r",
            ExpressionAttributeNames={"#s": "Status"},
            ExpressionAttributeValues={
                ":s": "accepted" if accept else "rejected",
                ":r": 1
            }
        )

        # Get both users
        from_data = user_table.get_item(Key={"UserId": from_user}).get("Item")
        to_data = user_table.get_item(Key={"UserId": to_user}).get("Item")
        if not from_data or not to_data:
            return _res(404, "One or both users not found.")

        # Notify the sender
        notif_table.put_item(
            Item={
                "NotifId": str(uuid4()),
                "FromUserId": to_user,
                "ToUserId": from_user,
                "Status": "accepted" if accept else "rejected",
                "IsRead": 0,
                "Text": f"{to_data.get('Username', 'Someone')} {'accepted' if accept else 'rejected'} your friend request.",
                "LinkId": "",
                "Timestamp": datetime.utcnow().isoformat()
            }
        )

        if not accept:
            return _res(200, "Friend request rejected.")

        # Update friend lists
        def parse_friends(user):
            raw = user.get("Friends", "[]")
            try:
                return set(json.loads(raw))
            except:
                return set()

        from_friends = parse_friends(from_data)
        to_friends = parse_friends(to_data)

        from_friends.add(to_user)
        to_friends.add(from_user)

        user_table.update_item(
            Key={"UserId": from_user},
            UpdateExpression="SET Friends = :f",
            ExpressionAttributeValues={":f": json.dumps(list(from_friends))}
        )
        user_table.update_item(
            Key={"UserId": to_user},
            UpdateExpression="SET Friends = :f",
            ExpressionAttributeValues={":f": json.dumps(list(to_friends))}
        )

        return _res(200, "Friend request accepted.")

    except Exception as e:
        print("[ERROR]", str(e))
        return _res(500, f"Unexpected server error: {str(e)}")

def _res(status, message):
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps({"message": message}, default=_decimal_default)
    }
