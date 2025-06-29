import json
import boto3
import os

# Initialize Boto3 clients
cognito_client = boto3.client('cognito-idp')
cloudformation_client = boto3.client('cloudformation')
dynamodb_resource = boto3.resource('dynamodb')

def get_env_prefix_from_context(context):
    """
    Parses the environment prefix from the Lambda function's name.
    Assumes the function name is formatted as '{env_prefix}-{logical-name}'.
    """
    function_name = context.function_name
    parts = function_name.rsplit('-', 1)
    if len(parts) > 1:
        return parts[0]
    print(f"WARNING: Could not determine environment prefix from function name '{function_name}'.")
    return None

def get_user_pool_id_from_stack(stack_name):
    """
    Dynamically fetches the User Pool ID from a given CloudFormation stack's outputs.
    """
    try:
        response = cloudformation_client.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0]['Outputs']
        for output in outputs:
            if output['OutputKey'].endswith('UserPoolP6ytmUserPoolId'):
                return output['OutputValue']
        return None
    except cloudformation_client.exceptions.ClientError as e:
        print(f"Could not describe stack '{stack_name}': {e}")
        return None

def get_username_from_dynamodb(user_id, table_name):
    """
    Fetches user details from DynamoDB using the user's sub (UserId).
    Extracts the Cognito username from the user's email address (part before '@').
    """
    try:
        table = dynamodb_resource.Table(table_name)
        response = table.get_item(Key={'UserId': user_id})
        
        item = response.get('Item')
        if not item:
            print(f"User with UserId '{user_id}' not found in DynamoDB table '{table_name}'.")
            return None
            
        email = item.get('Email')
        if not email or '@' not in email:
            print(f"Email attribute not found or invalid for user '{user_id}'.")
            return None
        
        # Split email and return the part before the '@' as the username
        username = email.split('@', 1)[0]
        return username
        
    except Exception as e:
        print(f"Error accessing DynamoDB table '{table_name}': {e}")
        return None

def lambda_handler(event, context):
    """
    Checks if a user is a member of the 'Admins' group by looking up their
    username in DynamoDB via their UserId (sub).
    """
    admin_group_name = os.environ.get('ADMIN_GROUP_NAME', 'Admins')

    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': ''
        }
    
    env_prefix = get_env_prefix_from_context(context)
    if env_prefix:
        cognito_stack_name = f"{env_prefix}-shortly-cognito"
        users_table_name = f"{env_prefix}-Users"
    else:
        print("Falling back to default names for Cognito stack and Users table.")
        cognito_stack_name = "shortly-cognito"
        users_table_name = "Users"
        
    user_pool_id = get_user_pool_id_from_stack(cognito_stack_name)
    if not user_pool_id:
        print(f"WARNING: Could not find User Pool ID from stack '{cognito_stack_name}'. Using hardcoded fallback ID.")
        user_pool_id = 'us-east-1_a30MYIcaj' # Your specified fallback
        
    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('UserId')

        if not user_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({'message': 'Bad Request: Missing UserId in request body.'})
            }
        
        # --- NEW LOGIC ---
        # Get the Cognito username from the Users table in DynamoDB
        cognito_username = get_username_from_dynamodb(user_id, users_table_name)
        
        if not cognito_username:
            # If we can't get the username (e.g., user not in DB), they can't be an admin.
            return {
                'statusCode': 200,
                'headers': { 'Access-Control-Allow-Origin': '*' },
                'body': json.dumps({'isAdmin': False, 'message': f'User {user_id} not found in {users_table_name}.'})
            }

        # Use the username from DynamoDB to check group membership
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=user_pool_id,
            Username=cognito_username
        )
        
        is_admin = any(group['GroupName'] == admin_group_name for group in response.get('Groups', []))

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({'isAdmin': is_admin})
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': { 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'message': 'Bad Request: Invalid JSON format.'})
        }
    except cognito_client.exceptions.UserNotFoundException:
        # This will catch if the username from DynamoDB (e.g., "admin") doesn't exist in Cognito.
        return {
            'statusCode': 200,
            'headers': { 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'isAdmin': False, 'message': 'User found in DynamoDB but not in Cognito User Pool.'})
        }
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            'statusCode': 500,
            'headers': { 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'message': 'An internal server error occurred.', 'error': str(e)})
        }


# Create a mock event with a test user ID
# mock_event = {
#     "body": json.dumps({
#         "UserId": "4488d498-20e1-70d5-3ad2-fa9eb8f64af1"
#     })
# }

# # Call the lambda handler with mock event
# class MockContext:
#     def __init__(self, function_name):
#         self.function_name = function_name

# # Create mock context with test function name
# mock_context = MockContext('short3-admin')

# # Call the lambda handler with mock event and context
# response = lambda_handler(mock_event, mock_context)

# # Print the response
# print(response)
