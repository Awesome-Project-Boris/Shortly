import json
import boto3
import os

# Initialize Boto3 clients
cognito_client = boto3.client('cognito-idp')
cloudformation_client = boto3.client('cloudformation')

def get_env_prefix_from_context(context):
    """
    Parses the environment prefix from the Lambda function's name.
    Assumes the function name is formatted as '{env_prefix}-{logical-name}'.
    For example, a function named 'dev-is-user-admin' will return 'dev'.
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

def lambda_handler(event, context):
    """
    Checks if a user is a member of the 'Admins' group in a Cognito User Pool.
    It dynamically determines its environment from the function name, with a fallback.
    """
    # Get the admin group name from an environment variable (this is fine to keep)
    admin_group_name = os.environ.get('ADMIN_GROUP_NAME', 'Admins')

    # Handle CORS preflight request
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
        stack_name = f"{env_prefix}-shortly-cognito"
    else:
        # If no prefix is found, fall back to the base name.
        print("Falling back to default stack name 'shortly-cognito'.")
        stack_name = "shortly-cognito"
        
    user_pool_id = get_user_pool_id_from_stack(stack_name)
    
    # FIX: Add a final fallback to a hardcoded User Pool ID if all other methods fail.
    if not user_pool_id:
        print(f"WARNING: Could not find User Pool ID from stack '{stack_name}'. Using hardcoded fallback ID.")
        user_pool_id = 'us-east-1_ZSxqwhOZ7'
        
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
        
        username = user_id

        # Check which groups the user belongs to
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=user_pool_id,
            Username=username
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
        return {
            'statusCode': 200,
            'headers': { 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'isAdmin': False, 'message': 'User not found in any groups.'})
        }
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {
            'statusCode': 500,
            'headers': { 'Access-Control-Allow-Origin': '*' },
            'body': json.dumps({'message': 'An internal server error occurred.', 'error': str(e)})
        }
