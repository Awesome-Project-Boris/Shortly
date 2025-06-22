import os
import json
import boto3
import uuid
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# --- Configuration ---
# It's best practice to use environment variables for table names.
# Provide default values based on your schema.
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
ACHIEVEMENTS_TABLE_NAME = os.environ.get('ACHIEVEMENTS_TABLE_NAME', 'Achievements')
USER_ACHIEVEMENTS_TABLE_NAME = os.environ.get('USER_ACHIEVEMENTS_TABLE_NAME', 'UserAchievements')
NOTIFICATIONS_TABLE_NAME = os.environ.get('NOTIFICATIONS_TABLE_NAME', 'Notifications')

# --- Achievement Milestones ---
# Maps a click count to a specific AchievementId from your Achievements table.
ACHIEVEMENT_MILESTONES = {
    25: '1',
    100: '2',
    1000: '3',
    10000: '4'
}

# Initialize DynamoDB resource and get table objects
dynamodb = boto3.resource('dynamodb')
links_table = dynamodb.Table(LINKS_TABLE_NAME)
achievements_table = dynamodb.Table(ACHIEVEMENTS_TABLE_NAME)
user_achievements_table = dynamodb.Table(USER_ACHIEVEMENTS_TABLE_NAME)
notifications_table = dynamodb.Table(NOTIFICATIONS_TABLE_NAME)


def lambda_handler(event, context):
    """
    Handles a link click: increments the click count, checks for and awards achievements,
    sends notifications, and finally redirects the user to the original URL.
    """
    # Extract short code (LinkId) from path parameters
    link_id = event.get('pathParameters', {}).get('code')
    if not link_id:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Missing link code parameter.'})}
        
    # --- Step 1: Fetch the Link Item ---
    try:
        response = links_table.get_item(Key={'LinkId': link_id})
        link_item = response.get('Item')
        if not link_item:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Link not found.'})}
    except ClientError as e:
        print(f"Error getting link: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': 'Could not retrieve link.'})}

    # --- NEW: Check if the clicker is the owner of the link ---
    # Get the userId of the person clicking from the query string
    clicker_user_id = event.get('queryStringParameters', {}).get('userId')
    link_owner_id = link_item.get('ownerId')

    # If the clicker's ID is provided and matches the link's ownerId, we skip the increment.
    if link_owner_id and clicker_user_id and link_owner_id == clicker_user_id:
        print(f"Owner '{link_owner_id}' clicked their own link '{link_id}'. Skipping count increment.")
    else:
        # --- Step 2: Increment Click Count (as a String) ---
        # This logic handles the requirement of storing NumberOfClicks as a string.
        # It reads the current value, increments it, and writes it back with a condition
        # to prevent race conditions.
        current_click_count_str = link_item.get('NumberOfClicks', '0')
        new_click_count = int(current_click_count_str) + 1
        
        try:
            links_table.update_item(
                Key={'LinkId': link_id},
                UpdateExpression='SET NumberOfClicks = :new_count',
                # ConditionExpression prevents overwriting if another process updated the count in the meantime.
                ConditionExpression='attribute_not_exists(NumberOfClicks) OR NumberOfClicks = :current_count',
                ExpressionAttributeValues={
                    ':new_count': str(new_click_count),
                    ':current_count': current_click_count_str
                }
            )
            print(f"Link '{link_id}' new click count: {new_click_count}")

        except ClientError as e:
            if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                # This means a race condition occurred. Another process updated the count.
                # We can refetch the item to get the absolute latest count.
                print("Race condition detected. Refetching item for accurate count.")
                response = links_table.get_item(Key={'LinkId': link_id})
                new_click_count = int(response.get('Item', {}).get('NumberOfClicks', '0'))
            else:
                print(f"Error updating click count: {e}")
                # The achievement check will use the last known count.
                new_click_count = int(link_item.get('NumberOfClicks', '0'))

        # --- Step 3: Check for Achievement Unlock ---
        if new_click_count in ACHIEVEMENT_MILESTONES:
            achievement_id_to_unlock = ACHIEVEMENT_MILESTONES[new_click_count]

            if link_owner_id:
                _handle_achievement_unlock(
                    user_id=link_owner_id,
                    link_item=link_item,
                    achievement_id=achievement_id_to_unlock,
                    click_count=new_click_count
                )
            else:
                print(f"Milestone reached for link '{link_id}', but no ownerId was found. Skipping achievement.")

    # --- Step 4: Redirect to the original URL ---
    # The 'String' attribute holds the original long URL
    original_url = link_item.get('String')
    if not original_url:
         return {'statusCode': 500, 'body': json.dumps({'error': 'Original URL not found for this link.'})}

    return {
        'statusCode': 301, # Permanent Redirect
        'headers': {
            'Location': original_url
        }
    }


def _handle_achievement_unlock(user_id, link_item, achievement_id, click_count):
    """
    A helper function to manage the process of awarding an achievement and sending a notification.
    """
    link_id = link_item['LinkId']
    link_name = link_item.get('Name', 'N/A')

    # --- Step 3a: Check if user already has this achievement FOR THIS SPECIFIC LINK ---
    # This check now uses a composite SortingKey to ensure uniqueness per user, per link, per achievement.
    sorting_key = f"{link_id}#{achievement_id}"
    
    try:
        response = user_achievements_table.get_item(
            Key={'UserId': user_id, 'SortingKey': sorting_key}
        )
        if 'Item' in response:
            print(f"User '{user_id}' already has achievement '{achievement_id}' for link '{link_id}'. Skipping award.")
            return # Exit the function if the achievement is already awarded
    except ClientError as e:
        print(f"Error checking for existing achievement: {e}")
        return # Exit on error

    print(f"User '{user_id}' unlocked achievement '{achievement_id}' for link '{link_id}'.")

    # --- Step 3b: Get Achievement Details ---
    try:
        response = achievements_table.get_item(Key={'AchievementId': achievement_id})
        achievement_item = response.get('Item', {})
        achievement_name = achievement_item.get('Name', f"Achievement #{achievement_id}")
    except ClientError as e:
        print(f"Could not fetch achievement name: {e}")
        achievement_name = f"Achievement #{achievement_id}"
    
    # --- Step 3c: Award the achievement ---
    try:
        user_achievements_table.put_item(
            Item={
                'UserId': user_id,
                'SortingKey': sorting_key, # The new composite key
                'AchievementId': achievement_id,
                'LinkId': link_id,
                'LinkName': link_name, # Storing this simplifies fetching data later
                'DateEarned': datetime.now(timezone.utc).isoformat()
            }
        )
    except ClientError as e:
        print(f"Error awarding achievement: {e}")
        return # If we can't award it, don't notify them.

    # --- Step 3d: Send a notification ---
    try:
        notification_text = (f"Your link '{link_name}' reached {click_count} clicks! "
                             f"You've earned the achievement: '{achievement_name}'.")
        
        notifications_table.put_item(
            Item={
                'NotifId': str(uuid.uuid4()),
                'ToUserId': user_id,
                'LinkId': link_id,
                'Text': notification_text,
                'IsRead': False,
                'Timestamp': datetime.now(timezone.utc).isoformat()
                # Status and FromUserId are left as null/not present as per your request
            }
        )
    except ClientError as e:
        print(f"Error creating notification: {e}")

