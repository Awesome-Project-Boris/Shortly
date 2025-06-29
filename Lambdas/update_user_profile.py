import json
import boto3
import os
from botocore.exceptions import ClientError

# --- Initialize AWS Clients ---
dynamodb = boto3.resource('dynamodb')

# --- Environment Variables ---
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')
users_table = dynamodb.Table(USERS_TABLE_NAME)

def _make_response(status_code, body):
    """Creates a fully CORS-compliant API response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,PUT,GET,DELETE'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    """
    Updates user profile information in DynamoDB.
    This version NO LONGER deletes anything from S3.
    """
    # --- CORS Preflight Handling ---
    if event.get('httpMethod') == 'OPTIONS':
        return _make_response(200, {})

    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId')

        if not user_id:
            return _make_response(400, {'message': 'Request must include "userId".'})

        # --- Build Update Expression for DynamoDB ---
        update_expression_parts = []
        expression_attribute_values = {}
        
        # Check for FullName and add to the update expression if present
        if 'FullName' in body:
            update_expression_parts.append("FullName = :fn")
            expression_attribute_values[':fn'] = body['FullName']
            
        # Check for Country and add to the update expression if present
        if 'Country' in body:
            update_expression_parts.append("Country = :c")
            expression_attribute_values[':c'] = body['Country']
            
        # Check for Picture and add to the update expression if present
        if 'Picture' in body:
            update_expression_parts.append("Picture = :p")
            expression_attribute_values[':p'] = body['Picture']
            
        if not update_expression_parts:
            return _make_response(400, {'message': 'No fields to update provided.'})
            
        update_expression = "SET " + ", ".join(update_expression_parts)

        # --- Perform the DynamoDB Update ---
        print(f"Updating profile for user: {user_id}")
        users_table.update_item(
            Key={'UserId': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression="attribute_exists(UserId)"
        )
        
        return _make_response(200, {'message': 'Profile updated successfully.'})

    except ClientError as e:
        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
            return _make_response(404, {'message': f"User with ID '{user_id}' not found."})
        print(f"DynamoDB Error: {e.response['Error']['Message']}")
        return _make_response(500, {'message': 'A database error occurred.'})

    except (json.JSONDecodeError, TypeError):
        return _make_response(400, {'message': 'Invalid JSON format in request body.'})

    except Exception as e:
        print(f"Unexpected error: {e}")
        return _make_response(500, {'message': 'An unexpected server error occurred.'})
