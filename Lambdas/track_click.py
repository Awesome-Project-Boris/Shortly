import os
import json
import boto3
import uuid
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from decimal import Decimal

# --- DynamoDB Table Names & Constants (Unchanged) ---
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
ACHIEVEMENTS_TABLE_NAME = os.environ.get('ACHIEVEMENTS_TABLE_NAME', 'Achievement')
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

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o)
        return super(DecimalEncoder, self).default(o)

def _create_response(status_code, body, encoder=None):
    """Creates a CORS-compliant API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(body, cls=encoder)
    }

def lambda_handler(event, context):
    """
    Handles a link click, increments count, and returns either the redirect URL
    or a flag indicating that a password is required.
    """
    if event.get('httpMethod') == 'OPTIONS':
        return _create_response(204, {})

    try:
        body = json.loads(event.get('body', '{}'))
        link_id = body.get('code')
        clicker_user_id = body.get('userId')
    except json.JSONDecodeError:
        return _create_response(400, {'error': 'Invalid JSON body.'})

    if not link_id:
        return _create_response(400, {'error': 'Missing link code in request body.'})
        
    try:
        response = links_table.get_item(Key={'LinkId': link_id})
        link_item = response.get('Item')
        # Also check if link is active
        if not link_item or not link_item.get('IsActive', True):
            return _create_response(404, {'error': 'Link not found or is inactive.'})
    except ClientError as e:
        print(f"Error getting link: {e}")
        return _create_response(500, {'error': 'Could not retrieve link.'})

    # --- Click Increment & Achievement Logic (Unchanged from your version) ---
    link_owner_id = link_item.get('UserId')
    new_click_count = int(link_item.get('NumberOfClicks', 0))

    if not (link_owner_id and clicker_user_id and link_owner_id == clicker_user_id):
        current_click_count = new_click_count
        new_click_count += 1
        try:
            links_table.update_item(
                Key={'LinkId': link_id},
                UpdateExpression='SET NumberOfClicks = :c',
                ExpressionAttributeValues={':c': new_click_count}
            )
            # Achievement check logic follows...
            for milestone, achievement_id in ACHIEVEMENT_MILESTONES.items():
                if new_click_count >= milestone:
                    if link_owner_id:
                        _handle_achievement_unlock(
                            user_id=link_owner_id,
                            link_item=link_item,
                            achievement_id=achievement_id,
                            click_count=milestone
                        )
        except ClientError as e:
            print(f"Error updating click count: {e}")
            new_click_count = current_click_count # Revert on error

    # --- MODIFIED RESPONSE LOGIC ---
    is_password_protected = link_item.get('IsPasswordProtected', False)
    
    if is_password_protected:
        # If protected, do not send the URL. Just confirm it's protected.
        return _create_response(200, {
            'isPasswordProtected': True
        })
    else:
        # If not protected, return the location for an immediate redirect.
        return _create_response(200, {
            'isPasswordProtected': False,
            'Location': link_item.get('String')
        })

# --- Helper Functions for Achievements ---

def _handle_achievement_unlock(user_id, link_item, achievement_id, click_count):
    """
    Awards an achievement, sends a notification, and updates the user's profile.
    """
    link_id = link_item['LinkId']
    sorting_key = f"{link_id}#{achievement_id}"
    
    try:
        # Prevent re-awarding the same achievement for the same link
        response = user_achievements_table.get_item(Key={'UserId': user_id, 'SortingKey': sorting_key})
        if 'Item' in response:
            print(f"User '{user_id}' already has achievement '{achievement_id}' for link '{link_id}'.")
            return
    except ClientError as e:
        print(f"Error checking existing achievement: {e}")
        return

    print(f"User '{user_id}' unlocking achievement '{achievement_id}' for link '{link_id}'.")

    # Get achievement details for the notification text
    try:
        # Using 'AchId' to match the table schema
        response = achievements_table.get_item(Key={'AchId': achievement_id})
        achievement_item = response.get('Item', {})
        achievement_name = achievement_item.get('Name', f"Achievement #{achievement_id}")
    except ClientError as e:
        print(f"Could not fetch achievement name: {e}")
        achievement_name = f"Achievement #{achievement_id}"
    
    # Create the entry in UserAchievements table
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

    # Update the User's own record with the new achievement
    _update_user_achievements_list(user_id, user_achievement_item)

    # Send a notification to the user
    try:
        notification_text = (f"Your link '{link_item.get('Name', 'N/A')}' reached {click_count} clicks! "
                             f"You've earned the achievement: '{achievement_name}'.")
        notifications_table.put_item(
            Item={
                'NotifId': str(uuid.uuid4()),
                'ToUserId': user_id,
                'LinkId': link_id,
                'Text': notification_text,
                'IsRead': 0, # MODIFIED: Set to integer 0 instead of boolean False
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
        # First, get the user item to check the 'Achievements' attribute
        user_item = users_table.get_item(Key={'UserId': user_id}).get('Item', {})
        existing_achievements = user_item.get('Achievements')

        # If 'Achievements' exists and is NOT a list (e.g., it's an empty string),
        # we overwrite it with the new achievement list.
        # Otherwise, we use list_append.
        if existing_achievements is not None and not isinstance(existing_achievements, list):
            print("DEBUG: 'Achievements' attribute is not a list. Overwriting.")
            update_expression = "SET Achievements = :new_achievement"
            expression_values = {':new_achievement': [achievement_data]}
        else:
            # This is the normal case: attribute is a list or doesn't exist yet.
            print("DEBUG: 'Achievements' is a list or does not exist. Appending.")
            update_expression = "SET Achievements = list_append(if_not_exists(Achievements, :empty_list), :new_achievement)"
            expression_values = {
                ':new_achievement': [achievement_data],
                ':empty_list': []
            }

        users_table.update_item(
            Key={'UserId': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
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
