import json
import boto3
import os
import traceback
from datetime import datetime, timedelta, timezone
from boto3.dynamodb.conditions import Key
from decimal import Decimal

# DynamoDB setup
dynamodb = boto3.resource("dynamodb")
notifications_table = dynamodb.Table(os.environ.get("NOTIFICATIONS_TABLE_NAME", "Notifications"))
users_table = dynamodb.Table(os.environ.get("USERS_TABLE_NAME", "Users"))
TOUSERID_INDEX_NAME = os.environ.get("TOUSERID_INDEX_NAME", "ToUserId-index")

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
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    try:
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("userId")

        if not user_id:
            return _res(400, {"message": "Missing 'userId' in request body."})

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        seven_days_ago_str = seven_days_ago.isoformat()

        response = notifications_table.query(
            IndexName=TOUSERID_INDEX_NAME,
            KeyConditionExpression=Key("ToUserId").eq(user_id)
        )
        notifications = response.get("Items", [])

        friend_requests = []
        other_notifications = []

        for notif in notifications:
            if notif.get("IsRead") == 0:
                if notif.get("Status") == "pending":
                    # Fetch the sender's username
                    sender_id = notif.get("FromUserId")
                    try:
                        sender = users_table.get_item(Key={"UserId": sender_id}).get("Item", {})
                        notif["Username"] = sender.get("Username", "Unknown")
                        notif["Picture"] = sender.get("Picture", "Unknown")
                    except Exception as e:
                        print(f"[WARN] Failed to fetch Username for {sender_id}: {e}")
                        notif["Username"] = "Unknown"
                        notif["Picture"] = "Unknown"

                    friend_requests.append(notif)

                elif notif.get("Timestamp", "") > seven_days_ago_str and notif.get("Status") in (None, "accepted", "rejected"):
                    other_notifications.append(notif)

        return _res(200, {
            "friendRequests": friend_requests,
            "otherNotifications": other_notifications
        })

    except Exception:
        print("[ERROR]", traceback.format_exc())
        return _res(500, {"message": "Unexpected server error."})

def _res(status, body):
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=_decimal_default)
    }
