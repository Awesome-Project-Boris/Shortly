import os
import json
import boto3
import uuid
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# --- DynamoDB Table Names ---
# Best practice to use environment variables with sensible defaults.
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
ACHIEVEMENTS_TABLE_NAME = os.environ.get('ACHIEVEMENTS_TABLE_NAME', 'Achievements')
USER_ACHIEVEMENTS_TABLE_NAME = os.environ.get('USER_ACHIEVEMENTS_TABLE_NAME', 'UserAchievements')
NOTIFICATIONS_TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications')
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users') # Added Users table

# --- Achievement Milestones ---
ACHIEVEMENT_MILESTONES = {
    25: '1',
    100: '2',
    1000: '3',
    10000: '4'
}

# --- Initialize DynamoDB ---
dynamodb = boto3.resource('dynamodb')
links_table = dynamodb.Table(LINKS_TABLE_NAME)
achievements_table = dynamodb.Table(ACHIEVEMENTS_TABLE_NAME)
user_achievements_table = dynamodb.Table(USER_ACHIEVEMENTS_TABLE_NAME)
notifications_table = dynamodb.Table(NOTIFICATIONS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME) # Added Users table resource

def lambda_handler(event, context):
    """
    Handles a link click: increments count, checks for achievements, and redirects.
    Skips incrementing if the clicker is the link owner.
    """
    link_id = event.get('pathParameters', {}).get('code')
    if not link_id:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Missing link code.'})}
        
    try:
        response = links_table.get_item(Key={'LinkId': link_id})
        link_item = response.get('Item')
        if not link_item:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Link not found.'})}
    except ClientError as e:
        print(f"Error getting link: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': 'Could not retrieve link.'})}

    clicker_user_id = event.get('queryStringParameters', {}).get('userId')
    link_owner_id = link_item.get('ownerId')

    if link_owner_id and clicker_user_id and link_owner_id == clicker_user_id:
        print(f"Owner '{link_owner_id}' clicked own link '{link_id}'. Skipping count increment.")
    else:
        current_click_count_str = link_item.get('NumberOfClicks', '0')
        new_click_count = int(current_click_count_str) + 1
        
        try:
            links_table.update_item(
                Key={'LinkId': link_id},
                UpdateExpression='SET NumberOfClicks = :new_count',
                ConditionExpression='attribute_not_exists(NumberOfClicks) OR NumberOfClicks = :current_count',
                ExpressionAttributeValues={
                    ':new_count': str(new_click_count),
                    ':current_count': current_click_count_str
                }
            )
            print(f"Link '{link_id}' new click count: {new_click_count}")

        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                print("Race condition on click count. Refetching.")
                response = links_table.get_item(Key={'LinkId': link_id})
                new_click_count = int(response.get('Item', {}).get('NumberOfClicks', '0'))
            else:
                print(f"Error updating click count: {e}")
                new_click_count = int(link_item.get('NumberOfClicks', '0'))

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
         return {'statusCode': 500, 'body': json.dumps({'error': 'Original URL not found.'})}

    return {'statusCode': 301, 'headers': {'Location': original_url}}

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
        response = achievements_table.get_item(Key={'AchievementId': achievement_id})
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

    # *** NEW: Update the User's own record with the new achievement ***
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
        # Using list_append to add the new achievement to the existing list.
        # If the 'Achievements' attribute doesn't exist, it will be created.
        users_table.update_item(
            Key={'UserId': user_id},
            UpdateExpression="SET Achievements = list_append(if_not_exists(Achievements, :empty_list), :new_achievement)",
            ExpressionAttributeValues={
                ':new_achievement': [achievement_data], # The item to append must be in a list
                ':empty_list': [] # Creates the list if it doesn't exist
            }
        )
        print(f"Successfully updated achievements list for user '{user_id}'.")
    except ClientError as e:
        print(f"Error updating user's achievements list: {e}")

