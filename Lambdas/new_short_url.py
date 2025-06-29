import os
import json
import string
import secrets
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB resources from environment variables
LINKS_TABLE_NAME = 'Links'
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users') # Table for user data

dynamodb = boto3.resource('dynamodb')
links_table = dynamodb.Table(LINKS_TABLE_NAME)
users_table = dynamodb.Table(USERS_TABLE_NAME) # Resource for the Users table


def generate_code(length: int = 8) -> str:
    """
    Generate a random base62 string for the short code.
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def lambda_handler(event, context):
    # --- CORS Preflight Handling ---
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 204,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': ''
        }
        
    # --- Parse and Validate Incoming Request ---
    try:
        body = json.loads(event.get('body', '{}'))
        long_url = body['url']
        user_id = body['userId']
    except (json.JSONDecodeError, KeyError):
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'error': 'Request must be JSON with "url" and "userId" fields.'})
        }

    # Extract optional fields with defaults
    name = body.get('name', '')
    description = body.get('description', '')
    is_private = bool(body.get('isPrivate', False))
    is_password_protected = bool(body.get('isPasswordProtected', False))
    password = body.get('password', '')

    # Validate password protection logic
    if is_password_protected and not password:
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({'error': 'Password must be provided when isPasswordProtected is true.'})
        }
    if not is_password_protected:
        password = ''  # enforce empty password when protection is off

    # --- Generate Unique LinkId ---
    code = generate_code()
    while True:
        resp = links_table.get_item(Key={'LinkId': code})
        if 'Item' not in resp:
            break
        code = generate_code()

    # --- Create Link Item in DynamoDB ---
    item = {
        'LinkId': code,
        'UserId': user_id,
        'String': long_url,
        'Name': name,
        'Description': description,
        'IsPrivate': is_private,
        'IsPasswordProtected': is_password_protected,
        'Password': password,
        'NumberOfClicks': 0,
        'Date': datetime.utcnow().isoformat(),
        'IsActive': True
    }
    links_table.put_item(Item=item)

    # --- MODIFIED: Update the User's 'Links' String Attribute ---
    try:
        print(f"Attempting to update user {user_id} with new link {code}")
        
        # 1. Get the current user item to read the existing Links string
        response = users_table.get_item(Key={'UserId': user_id})

        if 'Item' in response:
            user_item = response['Item']
            # Get the current JSON string of links, defaulting to an empty string
            current_links_json = user_item.get('Links', '')
            
            links_list = []
            # 2. Try to parse the existing JSON string into a list
            if current_links_json:
                try:
                    links_list = json.loads(current_links_json)
                    # Ensure it's a list, not some other JSON type
                    if not isinstance(links_list, list):
                        links_list = []
                except json.JSONDecodeError:
                    # Handle cases where the string is not valid JSON, start fresh
                    print(f"Warning: Could not parse existing Links attribute for user {user_id}. Starting a new list.")
                    links_list = []
            
            # 3. Append the new link code to the list
            links_list.append(code)
            
            # 4. Convert the list back to a JSON-formatted string
            new_links_json_string = json.dumps(links_list)
            
            # 5. Update the user item with the new JSON string
            users_table.update_item(
                Key={'UserId': user_id},
                UpdateExpression="SET Links = :l",
                ExpressionAttributeValues={':l': new_links_json_string}
            )
            print(f"Successfully updated user {user_id} with new links string.")
        else:
            print(f"User {user_id} not found. Cannot update Links attribute.")

    except ClientError as e:
        # Log the error but don't fail the entire request,
        # as the link was successfully created.
        print(f"Error updating Users table for user {user_id}: {e.response['Error']['Message']}")

    # --- Return Success Response ---
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'code': code})
    }

# Example test event
# if __name__ == "__main__":
#     test_event = {
#         'body': json.dumps({
#             'url': 'https://hianime.to/watch/one-piece-100',
#             'userId': 'lior1',
#             'name': 'Redirect Page Test Link',
#             'description': 'This is a test link',
#             'isPrivate': False,
#             'isPasswordProtected': False,
#             'password': ''
#         })
#     }
#     print(lambda_handler(test_event, None))
