import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Use an environment variable for the table name
MAILING_LISTS_TABLE_NAME = os.environ.get('MAILING_LISTS_TABLE_NAME', 'Mailing_Lists')
# The name of the GSI on the Mailing_Lists table
INITIATOR_ID_INDEX_NAME = 'InitiatorId-index'

def lambda_handler(event, context):
    """
    Fetches all mailing lists created by a specific user.
    
    Expects a JSON body with:
    - userId (string): The ID of the user whose groups are being requested.
    """
    
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    try:
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId')

        if not user_id:
            return {'statusCode': 400, 'headers': cors_headers, 'body': json.dumps({'message': 'userId is required in the request body.'})}

        mailing_lists_table = dynamodb.Table(MAILING_LISTS_TABLE_NAME)
        
        # --- Query the GSI to find all lists by the InitiatorId ---
        response = mailing_lists_table.query(
            IndexName=INITIATOR_ID_INDEX_NAME,
            KeyConditionExpression=boto3.dynamodb.conditions.Key('InitiatorId').eq(user_id),
            # Use a ProjectionExpression for efficiency: only return the attributes we need.
            ProjectionExpression="ListId, ListName"
        )
        
        groups = response.get('Items', [])

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(groups) # Return the list of groups directly
        }

    except ClientError as e:
        # This specific error is helpful for debugging if the GSI hasn't been created yet.
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"ERROR: GSI '{INITIATOR_ID_INDEX_NAME}' not found on table '{MAILING_LISTS_TABLE_NAME}'.")
            return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'Server configuration error.'})}
        
        print(f"DynamoDB ClientError: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'A database error occurred.'})}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'An unexpected server error occurred.'})}

