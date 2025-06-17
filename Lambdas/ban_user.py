import json
import boto3

dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table("Users")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("UserId")

        if not user_id:
            return _res(400, "Missing UserId")

        # Check if user exists
        resp = user_table.get_item(Key={"UserId": user_id})
        user = resp.get("Item")
        if not user:
            return _res(404, "User not found")

        # Update the isActive field
        user_table.update_item(
            Key={"UserId": user_id},
            UpdateExpression="SET isActive = :a",
            ExpressionAttributeValues={":a": "false"}
        )

        return _res(200, f"User {user_id} has been banned.")

    except Exception as e:
        return _res(500, str(e))


def _res(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": message})
    }
