import json
import boto3
import decimal
from boto3.dynamodb.conditions import Key

# Initialize DynamoDB resource and tables
# Note: Table names match the schema: 'User' and 'Links'
dynamodb = boto3.resource('dynamodb')
user_table = dynamodb.Table("Users")
link_table = dynamodb.Table("Links")


def decimal_default(obj):
    """
    JSON serializer for objects not serializable by default json code
    Converts Decimal to int or float.
    """
    if isinstance(obj, decimal.Decimal):
        # Convert whole numbers to int, others to float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def lambda_handler(event, context):
    '''
    Lambda function to retrieve all active, public links for a given user by querying the Links table via its UserId-index.
    Expects JSON body with 'UserId'.
    '''
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}") or "{}")
        user_id = body.get("UserId")

        if not user_id:
            return _response(400, {"message": "Missing UserId."})

        # Fetch user item
        resp = user_table.get_item(Key={"UserId": user_id})
        user = resp.get("Item")
        if not user:
            return _response(404, {"message": "User not found."})

        # Query Links table by UserId-index
        resp = link_table.query(
            IndexName="UserId-index",
            KeyConditionExpression=Key("UserId").eq(user_id)
        )
        items = resp.get("Items", [])

        links = []
        for link in items:
            # Only include active, public links
            if link.get("IsActive") and not link.get("IsPrivate"):
                link.pop("Password", None)
                link.pop("IsPasswordProtected", None)
                links.append(link)

        return _response(200, {"links": links})

    except Exception as e:
        return _response(500, {"message": str(e)})


def _response(status_code, body):
    '''
    Helper to format HTTP JSON responses with Decimal support.
    '''
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        # Use custom default handler to convert Decimal types
        "body": json.dumps(body, default=decimal_default)
    }



# Create mock event
mock_event = {
    "body": json.dumps({
        "UserId": "a1"
    })
}

# Call lambda handler with mock event
response = lambda_handler(mock_event, None)
print(response)