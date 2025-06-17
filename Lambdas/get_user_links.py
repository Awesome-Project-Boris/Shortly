import json
import boto3

dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table("Users")
link_table = dynamodb.Table("Link")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        user_id = body.get("UserId")

        if not user_id:
            return _res(400, "Missing UserId.")

        # Get the user
        user_resp = user_table.get_item(Key={"UserId": user_id})
        user = user_resp.get("Item")

        if not user or user.get("isActive") != "true":
            return _res(403, "User not found or inactive.")

        # Parse their link IDs
        raw_links = user.get("Links", "")
        link_ids = json.loads(raw_links) if raw_links else []

        links = []
        for link_id in link_ids:
            link_resp = link_table.get_item(Key={"LinkId": link_id})
            link = link_resp.get("Item")
            if link:
                links.append(link)

        return _res(200, links)

    except Exception as e:
        return _res(500, str(e))


def _res(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"data": body} if isinstance(body, list) else {"message": body})
    }
