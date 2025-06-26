import os
import json
import boto3
from botocore.exceptions import ClientError

# --- Initialize DynamoDB ---
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links') # Corrected ENV var name for consistency
links_table = dynamodb.Table(TABLE_NAME)

def _make_response(status_code, body):
    """
    Centralized function to create API responses with full CORS headers.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            # Allow all methods your front-end might use for this type of resource
            'Access-Control-Allow-Methods': 'OPTIONS,POST,DELETE'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    """
    AWS Lambda entry point: deactivates a link by setting its IsActive flag to False.
    """
    # --- CORS Preflight Handling ---
    # This block handles the browser's initial OPTIONS request.
    if event.get('httpMethod') == 'OPTIONS':
        return _make_response(204, {})

    # 1. Parse and validate input parameters
    try:
        raw_body = event.get('body', '{}') # Use get() for safety
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        link_id = body.get('LinkId')  # Use get() for safety
        if not link_id:
            raise KeyError('LinkId is a required field.')
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        return _make_response(400, {'error': f'Missing or invalid input: {str(e)}'})

    try:
        # 2. Perform update: set IsActive to False, only if the item exists
        links_table.update_item(
            Key={'LinkId': link_id},
            UpdateExpression='SET IsActive = :false_val',
            ExpressionAttributeValues={':false_val': False},
            ConditionExpression='attribute_exists(LinkId)'
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ConditionalCheckFailedException':
            # Handle conditional check failure (item doesn't exist)
            return _make_response(404, {'error': 'Link not found'})
        
        # Handle other DynamoDB errors
        print(f"DynamoDB Error: {e.response['Error']['Message']}")
        return _make_response(500, {'error': 'Unable to deactivate link.'})

    # 3. Return success response
    return _make_response(200, {'message': 'Link deactivated successfully.'})

# Create a mock event with a sample LinkId
# mock_event = {
#     'httpMethod': 'DELETE', # or POST
#     'body': json.dumps({
#         'LinkId': 'gjJ4OGlx'
#     })
# }

# # Call the lambda handler with the mock event
# response = lambda_handler(mock_event, None)

# # Print the response
# print(json.dumps(response, indent=2))
