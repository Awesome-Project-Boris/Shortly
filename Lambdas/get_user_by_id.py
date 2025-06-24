import os
import json
import boto3
import decimal
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# --- Initialize DynamoDB and Table Resources ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE', 'Users')
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
USER_ACHIEVEMENTS_TABLE_NAME = os.environ.get('USER_ACHIEVEMENTS_TABLE_NAME', 'UserAchievements')

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE_NAME)
links_table = dynamodb.Table(LINKS_TABLE_NAME)
user_achievements_table = dynamodb.Table(USER_ACHIEVEMENTS_TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        profile_owner_id = body.get('ProfileOwnerId')
        logged_in_user_id = body.get('LoggedInUserId')

        if not profile_owner_id:
            return _make_response(400, {'error': 'ProfileOwnerId is a required field.'})

    except (json.JSONDecodeError, TypeError):
        return _make_response(400, {'error': 'Invalid JSON format in request body.'})

    try:
        user_info = _get_user_info(profile_owner_id)
        if not user_info:
            return _make_response(404, {'error': 'User not found.'})

        achievements = _get_user_achievements(profile_owner_id)
        links = _get_user_links_without_gsi(profile_owner_id)

    except ClientError as e:
        print(f"DynamoDB Error: {e.response['Error']['Message']}")
        return _make_response(500, {'error': 'An error occurred while fetching profile data.'})

    is_owner_viewing = profile_owner_id == logged_in_user_id
    if not is_owner_viewing:
        links = [link for link in links if not link.get('IsPrivate', False)]

    response_payload = {
        'userInfo': user_info,
        'achievements': achievements,
        'links': links
    }

    return _make_response(200, response_payload)


def _get_user_info(user_id):
    response = users_table.get_item(
        Key={'UserId': user_id},
        ProjectionExpression="UserId, Username, FullName, Country, DateJoined, IsActive, Picture"
    )
    return response.get('Item')


def _get_user_achievements(user_id):
    response = user_achievements_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('UserId').eq(user_id)
    )
    return response.get('Items', [])


def _get_user_links_without_gsi(user_id):
    """Scans the Links table and filters by ownerId (used instead of GSI)."""
    results = []
    response = links_table.scan(
        FilterExpression=Attr('ownerId').eq(user_id)
    )
    results.extend(response.get('Items', []))

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = links_table.scan(
            FilterExpression=Attr('ownerId').eq(user_id),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        results.extend(response.get('Items', []))

    return results


def _make_response(status_code, body):
    return {
        'statusCode': status_code,
        "headers": {
            "Content-Type": "application/json",
            'Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            'Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
            'Access-Control-Allow-Origin': "*"
                },
        'body': json.dumps(body, cls=DecimalEncoder)
    }
