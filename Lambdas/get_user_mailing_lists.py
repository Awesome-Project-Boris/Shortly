import json
import boto3
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr # Import Attr for Scan FilterExpression

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Use an environment variable for the table name
TABLE_NAME = os.environ.get('MAILING_LISTS_TABLE_NAME', 'Mailing_Lists')
# INDEX_NAME is no longer needed for a Scan operation
# INDEX_NAME = os.environ.get('INITIATOR_ID_INDEX_NAME', 'InitiatorId-index')

def lambda_handler(event, context):
    """
    Handles API Gateway requests.
    - Responds to preflight OPTIONS requests for CORS.
    - On POST, fetches mailing lists for a given InitiatorId using a Scan.
    """
    
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 204,
            'headers': cors_headers,
            'body': ''
        }

    try:
        body = json.loads(event.get('body', '{}'))
        initiator_id = body.get('InitiatorId')

        if not initiator_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'InitiatorId is required.'})
            }

        table = dynamodb.Table(TABLE_NAME)
        
        # --- MODIFIED SECTION: Using Scan instead of Query ---
        # A Scan reads the entire table and then filters, which can be inefficient.
        response = table.scan(
            # FilterExpression is used to narrow down results AFTER the scan
            FilterExpression=Attr('InitiatorId').eq(initiator_id),
            # ProjectionExpression is still useful to limit the data returned
            ProjectionExpression="ListId, ListName"
        )
        # --- END OF MODIFIED SECTION ---
        
        groups = response.get('Items', [])

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(groups)
        }

    except ClientError as e:
        print(f"DynamoDB ClientError: {e.response['Error']['Message']}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'Database error occurred.'})}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'An unexpected server error occurred.'})}