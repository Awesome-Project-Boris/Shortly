import boto3
import json
from datetime import datetime

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Specify your DynamoDB table name
USER_TABLE = "Users" # !!replace with your table name!!

# Reference to the DynamoDB table
user_table = dynamodb.Table(USER_TABLE)

def lambda_handler(event, context):
    # Extract user details from the Cognito event
    email = event['Email']  # Unique identifier for the user
    user_attributes = event['request']['userAttributes']
    
    # Get the current timestamp for the creationDate in the desired format
    creation_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')  # Format as YYYY-MM-DDTHH:MM:SS
    
    # Prepare the user data to insert into DynamoDB
    user_data = {
        'UserId': user_attributes.get('sub', 'Unknown'),  # 'sub' is the unique identifier in Cognito
        'Username': user_attributes.get('username'),
        'Nickname': user_attributes.get('nickname', 'unknown'),
        'Email': email,
        'FullName': user_attributes.get('name', 'Unknown'),
        'Country': user_attributes.get('locale','Unknown'),
        'DateJoined': creation_date,  # Add the current creation date in the desired format
        'IsActive': True,
        'Picture': user_attributes.get('picture', 'images/profile-photos/default-user.png'),
        'Friends': "",
        'Email': email,
        'Links': "",
        'Notifications': "",
        'Achievements': "",
        'LinksClickedId': "",
    }

    try:
        # Add user to DynamoDB
        user_table.put_item(Item=user_data)
        print(f"User {email} added successfully to DynamoDB.")

        # Return the event back to Cognito
        return event

    except Exception as e:
        print(f"Error adding user {email} to DynamoDB: {str(e)}")
        raise
    
    