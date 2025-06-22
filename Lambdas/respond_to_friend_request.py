import json
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from uuid import uuid4

dynamodb = boto3.resource('dynamodb')
notif_table = dynamodb.Table("Notifications")
user_table = dynamodb.Table("Users")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        notification_id = body.get("NotifId")
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

        # Mark original as read and update status
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

        # Send notification to original sender
        notif_table.put_item(
            Item={
                "NotifId": str(uuid4()),
                "FromUserId": to_user,         # The one responding
                "ToUserId": from_user,         # The one who sent original request
                "Status": "accepted" if accept else "rejected",
                "IsRead": 0,
                "Text": f"{to_data.get('Username', 'Someone')} {'accepted' if accept else 'rejected'} your friend request.",
                "LinkId": "",
                "Timestamp": datetime.utcnow().isoformat()
            }
        )

        if not accept:
            return _res(200, "Friend request rejected.")

        # Add each other as friends
        def parse_friends(user):
            raw = user.get("Friends", "")
            return set(json.loads(raw)) if raw else set()

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
        return _res(500, str(e))


def _res(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message})
    }





 # Example Request Body for Testing
        # {
        #   "NotificationId": "b5a1c0d1-30fd-4022-a3cf-0a2c456789ab",  
        #   "accept": True
        # }