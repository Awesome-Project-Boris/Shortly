import os
import json
import boto3
import decimal
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

# --- Initialize DynamoDB and Table Resources ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
USER_ACHIEVEMENTS_TABLE_NAME = os.environ.get('USER_ACHIEVEMENTS_TABLE_NAME', 'UserAchievements')
ACHIEVEMENTS_TABLE_NAME = os.environ.get('ACHIEVEMENTS_TABLE_NAME', 'Achievement')
LINKS_USERID_GSI_NAME = os.environ.get('LINKS_USERID_GSI_NAME', 'UserId-index')


dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE_NAME)
links_table = dynamodb.Table(LINKS_TABLE_NAME)
user_achievements_table = dynamodb.Table(USER_ACHIEVEMENTS_TABLE_NAME)
achievements_table = dynamodb.Table(ACHIEVEMENTS_TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return _make_response(204, {})

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
        # This function will now fetch only active links
        links = _get_user_links_with_gsi(profile_owner_id)

    except ClientError as e:
        print(f"DynamoDB Error: {e.response['Error']['Message']}")
        return _make_response(500, {'error': 'An error occurred while fetching profile data.'})

    is_owner_viewing = profile_owner_id == logged_in_user_id
    if not is_owner_viewing:
        # This privacy filter is now applied to the list of *active* links
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
    user_ach_response = user_achievements_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('UserId').eq(user_id)
    )
    earned_achievements = user_ach_response.get('Items', [])
    
    enriched_achievements = []
    
    for ach in earned_achievements:
        achievement_id = ach.get('AchievementId')
        if not achievement_id:
            continue
            
        try:
            master_ach_response = achievements_table.get_item(
                Key={'AchId': achievement_id}
            )
            
            if 'Item' in master_ach_response:
                ach['Achievement'] = master_ach_response['Item']
                
            enriched_achievements.append(ach)
            
        except ClientError as e:
            print(f"Could not fetch details for AchievementId {achievement_id}: {e}")
            enriched_achievements.append(ach)

    return enriched_achievements


def _get_user_links_with_gsi(user_id):
    """
    MODIFIED: Queries the Links table's GSI and filters to return only active links.
    """
    results = []
    
    # This FilterExpression ensures we only get items where 'IsActive' is true.
    # We also include items where the attribute doesn't exist, for backward compatibility.
    filter_expression = Attr('IsActive').eq(True) | Attr('IsActive').not_exists()
    
    # Using a paginator is a more efficient way to handle queries that might return many items.
    paginator = links_table.get_paginator('query')
    pages = paginator.paginate(
        IndexName=LINKS_USERID_GSI_NAME,
        KeyConditionExpression=Key('UserId').eq(user_id),
        FilterExpression=filter_expression
    )
    
    for page in pages:
        results.extend(page.get('Items', []))

    return results


def _make_response(status_code, body):
    return {
        'statusCode': status_code,
        "headers": {
            "Content-Type": "application/json",
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Origin': "*"
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }
