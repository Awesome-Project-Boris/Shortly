import os
import json
import boto3
import decimal
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# --- Initialize DynamoDB and Table Resources ---
# Using environment variables is a best practice for table names.
USERS_TABLE_NAME = os.environ.get('USERS_TABLE', 'Users')
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
USER_ACHIEVEMENTS_TABLE_NAME = os.environ.get('USER_ACHIEVEMENTS_TABLE_NAME', 'UserAchievements')

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE_NAME)
links_table = dynamodb.Table(LINKS_TABLE_NAME)
user_achievements_table = dynamodb.Table(USER_ACHIEVEMENTS_TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """
    Helper class to convert a DynamoDB item's Decimal types to JSON-compatible int/float.
    """
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 == 0:
                return int(o)
            else:
                return float(o)
        return super(DecimalEncoder, self).default(o)

def lambda_handler(event, context):
    """
    Fetches a user's profile data, including public info, achievements, and links.
    - It distinguishes between a profile owner and a logged-in visitor.
    - Private links are only returned if the visitor is the owner.
    """
    try:
        body = json.loads(event.get('body', '{}'))
        profile_owner_id = body.get('ProfileOwnerId')
        # LoggedInUserId can be optional for viewing public profiles
        logged_in_user_id = body.get('LoggedInUserId') 

        if not profile_owner_id:
            return _make_response(400, {'error': 'ProfileOwnerId is a required field.'})
    except (json.JSONDecodeError, TypeError):
        return _make_response(400, {'error': 'Invalid JSON format in request body.'})

    # --- Fetch Data in Parallel ---
    # This approach is more complex to implement with boto3 resource directly.
    # For simplicity, we'll fetch sequentially. For high performance, consider asyncio with aioboto3.
    
    try:
        # 1. Get User's Public Info
        # ProjectionExpression ensures we only fetch specified attributes.
        user_info = _get_user_info(profile_owner_id)
        if not user_info:
            return _make_response(404, {'error': 'User not found.'})
            
        # 2. Get User's Achievements
        achievements = _get_user_achievements(profile_owner_id)
        
        # 3. Get User's Links
        links = _get_user_links(profile_owner_id)

    except ClientError as e:
        print(f"DynamoDB Error: {e}")
        return _make_response(500, {'error': 'An error occurred while fetching profile data.'})

    # --- Filter Links Based on Privacy ---
    is_owner_viewing = profile_owner_id == logged_in_user_id
    
    if not is_owner_viewing:
        # Filter out private links if the viewer is not the owner.
        # A link is considered public if 'IsPrivate' is False or the attribute doesn't exist.
        filtered_links = [link for link in links if not link.get('IsPrivate', False)]
    else:
        # The owner sees all their links.
        filtered_links = links

    # --- Construct Final Response ---
    response_payload = {
        'userInfo': user_info,
        'achievements': achievements,
        'links': filtered_links
    }

    return _make_response(200, response_payload)

def _get_user_info(user_id):
    """Fetches a limited set of public user attributes."""
    response = users_table.get_item(
        Key={'UserId': user_id},
        ProjectionExpression="UserId, Username, FullName, Country, DateJoined, IsActive, Picture"
    )
    return response.get('Item')

def _get_user_achievements(user_id):
    """Fetches all achievements for a given user."""
    response = user_achievements_table.query(
        KeyConditionExpression=Key('UserId').eq(user_id)
    )
    return response.get('Items', [])

def _get_user_links(user_id):
    """Fetches all links created by a given user using the 'ownerId-index'."""
    response = links_table.query(
        IndexName='ownerId-index',  # Assumes a GSI on the 'ownerId' attribute
        KeyConditionExpression=Key('ownerId').eq(user_id)
    )
    return response.get('Items', [])

def _make_response(status_code, body):
    """Helper function to format the Lambda proxy response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*' # CORS header for frontend access
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }

