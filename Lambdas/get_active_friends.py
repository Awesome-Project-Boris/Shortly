import json
import boto3

dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table("Users")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("UserId")

        if not user_id:
            return _res(400, "Missing UserId.")

        # Get the requesting user
        resp = user_table.get_item(Key={"UserId": user_id})
        user = resp.get("Item")
        if not user or user.get("IsActive") != "true":
            return _res(403, "User not found or inactive.")

        # Parse friend list
        raw_friends = user.get("Friends", "")
        friend_ids = json.loads(raw_friends) if raw_friends else []

        results = []
        for fid in friend_ids:
            f_resp = user_table.get_item(Key={"UserId": fid})
            f_user = f_resp.get("Item")
            if f_user and f_user.get("IsActive") == "true":
                results.append({
                    "UserId": f_user["UserId"],
                    "FullName": f_user.get("FullName", ""),
                    "Email": f_user.get("Email", "")
                })

        return _res(200, results)

    except Exception as e:
        return _res(500, str(e))


def _res(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"data": body} if isinstance(body, list) else {"message": body})
    }
