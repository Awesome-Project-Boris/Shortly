import boto3  # AWS SDK for Python (boto3) to interact with DynamoDB
import json  # For parsing and generating JSON payloads
from datetime import datetime  # To generate timestamp for user creation

# Initialize DynamoDB resource once (reused across Lambda invocations)
_dynamodb = boto3.resource('dynamodb')

# Name of your DynamoDB table that stores user records
USER_TABLE = "Users"  # Replace with your actual table name if different
user_table = _dynamodb.Table(USER_TABLE)

def lambda_handler(event, context):
    """
    Entry point for the Lambda function when invoked via API Gateway.
    This function reads user details from the request body, formats a new user item,
    and writes it to DynamoDB, returning an HTTP response dictionary.
    """
    try:
        # ----------------------------------------------------------------------------
        # 1. Parse incoming HTTP request body (API Gateway proxy integration)
        # ----------------------------------------------------------------------------
        body_json = event.get('body', '{}')  # Raw string from API Gateway
        body = json.loads(body_json)         # Convert JSON string to Python dict

        # Retrieve the mandatory fields from the parsed body
        email = body.get('Email')  # User's email; used as a unique login identifier
        # userAttributes block follows the structure used by Cognito triggers
        user_attributes = body.get('request', {}).get('userAttributes', {})

        # ----------------------------------------------------------------------------
        # 2. Input validation: ensure essential data is present
        # ----------------------------------------------------------------------------
        if not email or not user_attributes:
            # Bad request: missing either Email or the nested user attributes
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'message': 'Request must include Email and request.userAttributes'
                })
            }

        # ----------------------------------------------------------------------------
        # 3. Compute creation timestamp in ISO format (UTC)
        # ----------------------------------------------------------------------------
        creation_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')

        # ----------------------------------------------------------------------------
        # 4. Assemble the DynamoDB item with defaults for optional fields
        # ----------------------------------------------------------------------------
        user_data = {
            'UserId': user_attributes.get('sub', 'Unknown'),                          # Cognito 'sub' is the unique user ID
            'Username': user_attributes.get('username'),                               # Cognito username
            'Nickname': user_attributes.get('nickname', 'unknown'),                   # Fallback to 'unknown' if not provided
            'Email': email,                                                           # Email extracted above
            'FullName': user_attributes.get('name', 'Unknown'),                       # User's full name or 'Unknown'
            'Country': user_attributes.get('locale', 'Unknown'),                      # Locale field often holds country code
            'DateJoined': creation_date,                                              # Timestamp of when record was created
            'IsActive': True,                                                         # Default new users to active
            'Picture': user_attributes.get('picture', 'images/profile-photos/default-user.png'),
            'Friends': "",           # Stored as JSON string of friend records; empty until populated
            'Links': "",             # JSON string of link IDs owned by user
            'Notifications': "",     # JSON string for notifications
            'Achievements': "",      # JSON string for user achievements
            'LinksClickedId': ""     # JSON string tracking clicked link IDs
        }

        # ----------------------------------------------------------------------------
        # 5. Persist the new user record in DynamoDB
        # ----------------------------------------------------------------------------
        user_table.put_item(Item=user_data)

        # ----------------------------------------------------------------------------
        # 6. Return a success response (HTTP 201 Created)
        # ----------------------------------------------------------------------------
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': f'User {email} created successfully',
                'user': user_data  # Echo back the created record for confirmation
            })
        }

    except Exception as e:
        # ----------------------------------------------------------------------------
        # Error handling: log exception and return 500 Internal Server Error
        # ----------------------------------------------------------------------------
        print(f"Error creating user record: {str(e)}")  # CloudWatch log for debugging
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Internal server error'})
        }

# Create a mock event with test data
# test_event = {
#     "body": json.dumps({
#         "Email": "test@example.com",
#         "request": {
#             "userAttributes": {
#                 "sub": "abc123",
#                 "username": "testuser",
#                 "nickname": "tester",
#                 "name": "Test User",
#                 "locale": "US",
#                 "picture": "images/profile-photos/test.jpg"
#             }
#         }
#     })
# }

# # Call the lambda handler with the test event
# response = lambda_handler(test_event, None)

# # Print the response
# print(json.dumps(response, indent=2))