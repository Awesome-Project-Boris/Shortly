import os
import json
import boto3
import uuid
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from decimal import Decimal

# --- DynamoDB Table Names & Constants (Unchanged) ---
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
ACHIEVEMENTS_TABLE_NAME = os.environ.get('ACHIEVEMENTS_TABLE_NAME', 'Achievements')
USER_ACHIEVEMENTS_TABLE_NAME = os.environ.get('USER_ACHIEVEMENTS_TABLE_NAME', 'UserAchievements')
NOTIFICATIONS_TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications')
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')

ACHIEVEMENT_MILESTONES = {
    25: '1',
    100: '2',
    1000: '3',
    10000: '4'
}

# --- Initialize DynamoDB (Unchanged) ---
dynamodb = boto3.resource('dynamodb')
links_table = dynamodb.Table(LINKS_TABLE_NAME)
achievements_table = dynamodb.Table(ACHIEVEMENTS_TABLE_NAME)
user_achievements_table = dynamodb.Table(USER_ACHIEVEMENTS_TABLE_NAME)
notifications_table = dynamodb.Table(NOTIFICATIONS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME)

# --- Helper Classes & Functions ---

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o)
        return super(DecimalEncoder, self).default(o)

def _create_response(status_code, body, encoder=None):
    """
    NEW: Centralized function to create API responses with full CORS headers.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(body, cls=encoder)
    }

# --- Main Lambda Handler ---

def lambda_handler(event, context):
    """
    Handles a link click from the redirector page with robust CORS handling.
    """
    # NEW: Handle preflight OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return _create_response(204, {})

    try:
        body = json.loads(event.get('body', '{}'))
        link_id = body.get('code')
        clicker_user_id = body.get('userId')
    except json.JSONDecodeError:
        # MODIFIED: Use the response helper
        return _create_response(400, {'error': 'Invalid JSON body.'})

    if not link_id:
        # MODIFIED: Use the response helper
        return _create_response(400, {'error': 'Missing link code in request body.'})
        
    try:
        response = links_table.get_item(Key={'LinkId': link_id})
        link_item = response.get('Item')
        if not link_item:
            # MODIFIED: Use the response helper
            return _create_response(404, {'error': 'Link not found.'})
    except ClientError as e:
        print(f"Error getting link: {e}")
        # MODIFIED: Use the response helper
        return _create_response(500, {'error': 'Could not retrieve link.'})

    link_owner_id = link_item.get('UserId')

    # Default to current click count in case the owner clicks their own link
    new_click_count = int(link_item.get('NumberOfClicks', 0))

    if link_owner_id and clicker_user_id and link_owner_id == clicker_user_id:
        print(f"Owner '{link_owner_id}' clicked own link '{link_id}'. Skipping count increment.")
    else:
        current_click_count = int(link_item.get('NumberOfClicks', 0))
        new_click_count = current_click_count + 1
        
        try:
            links_table.update_item(
                Key={'LinkId': link_id},
                UpdateExpression='SET NumberOfClicks = :new_count',
                ConditionExpression='attribute_not_exists(NumberOfClicks) OR NumberOfClicks = :current_count',
                ExpressionAttributeValues={
                    ':new_count': new_click_count,
                    ':current_count': current_click_count
                }
            )
            print(f"Link '{link_id}' new click count: {new_click_count}")
        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                print("Race condition on click count. Refetching.")
                response = links_table.get_item(Key={'LinkId': link_id})
                new_click_count = int(response.get('Item', {}).get('NumberOfClicks', 0))
            else:
                print(f"Error updating click count: {e}")
                new_click_count = current_click_count # Revert to last known good count on error

    if new_click_count in ACHIEVEMENT_MILESTONES:
        achievement_id_to_unlock = ACHIEVEMENT_MILESTONES[new_click_count]
        if link_owner_id:
            _handle_achievement_unlock(
                user_id=link_owner_id,
                link_item=link_item,
                achievement_id=achievement_id_to_unlock,
                click_count=new_click_count
            )
    
    original_url = link_item.get('String')
    if not original_url:
        # MODIFIED: Use the response helper
        return _create_response(500, {'error': 'Original URL not found.'})

    # MODIFIED: Use the response helper for the final success response
    return _create_response(200, {'Location': original_url}, encoder=DecimalEncoder)

# --- Helper Functions for Achievements (Unchanged) ---
# The bodies of these functions are unchanged from your file.

def _handle_achievement_unlock(user_id, link_item, achievement_id, click_count):
    """
    Awards an achievement, sends a notification, and updates the user's profile.
    """
    link_id = link_item['LinkId']
    sorting_key = f"{link_id}#{achievement_id}"
    
    try:
        response = user_achievements_table.get_item(Key={'UserId': user_id, 'SortingKey': sorting_key})
        if 'Item' in response:
            print(f"User '{user_id}' already has achievement '{achievement_id}' for link '{link_id}'.")
            return
    except ClientError as e:
        print(f"Error checking existing achievement: {e}")
        return

    print(f"User '{user_id}' unlocking achievement '{achievement_id}' for link '{link_id}'.")

    try:
        response = achievements_table.get_item(Key={'AchievementId': achievement_id})
        achievement_item = response.get('Item', {})
        achievement_name = achievement_item.get('Name', f"Achievement #{achievement_id}")
    except ClientError as e:
        print(f"Could not fetch achievement name: {e}")
        achievement_name = f"Achievement #{achievement_id}"
    
    try:
        user_achievement_item = {
            'UserId': user_id,
            'SortingKey': sorting_key,
            'AchievementId': achievement_id,
            'LinkId': link_id,
            'LinkName': link_item.get('Name', 'N/A'),
            'DateEarned': datetime.now(timezone.utc).isoformat()
        }
        user_achievements_table.put_item(Item=user_achievement_item)
    except ClientError as e:
        print(f"Error awarding achievement: {e}")
        return

    _update_user_achievements_list(user_id, user_achievement_item)

    try:
        notification_text = (f"Your link '{link_item.get('Name', 'N/A')}' reached {click_count} clicks! "
                             f"You've earned the achievement: '{achievement_name}'.")
        notifications_table.put_item(
            Item={
                'NotifId': str(uuid.uuid4()),
                'ToUserId': user_id,
                'LinkId': link_id,
                'Text': notification_text,
                'IsRead': False,
                'Timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
    except ClientError as e:
        print(f"Error creating notification: {e}")

def _update_user_achievements_list(user_id, achievement_data):
    """
    Appends a new achievement object to the 'Achievements' list in the Users table.
    """
    try:
        users_table.update_item(
            Key={'UserId': user_id},
            UpdateExpression="SET Achievements = list_append(if_not_exists(Achievements, :empty_list), :new_achievement)",
            ExpressionAttributeValues={
                ':new_achievement': [achievement_data],
                ':empty_list': []
            }
        )
        print(f"Successfully updated achievements list for user '{user_id}'.")
    except ClientError as e:
        print(f"Error updating user's achievements list: {e}")


# test_event = {
#     "body": json.dumps({
#         "code": "test-link-123",
#         "userId": "test-user-456"
#     }),
#     "headers": {
#         "Content-Type": "application/json"
#     }
# }

# # Call lambda handler with test event
# response = lambda_handler(test_event, None)

# # Print response
# print(json.dumps(response, indent=2))