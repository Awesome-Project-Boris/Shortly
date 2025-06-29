import os
import json
import uuid
import boto3
from botocore.exceptions import ClientError

# --- Initialize DynamoDB resource ---
dynamodb = boto3.resource('dynamodb')
MAILING_LISTS_TABLE_NAME = os.environ.get('MAILING_LISTS_TABLE_NAME', 'Mailing_Lists')
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')

def lambda_handler(event, context):
    """
    AWS Lambda function to create a new mailing list.
    Accepts a list of friend IDs and a list of loose emails,
    combines them, and saves the group.
    """
    
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'CORS pre-flight check successful.'})
        }

    try:
        raw_body = event.get('body', '{}')
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

        initiator_id = body['initiatorId']
        list_name = body.get('name', '')
        # Accept both lists from the front-end
        recipient_ids = body.get('recipientsIds', [])
        loose_emails = body.get('recipientsEmails', [])

        if not isinstance(recipient_ids, list) or not isinstance(loose_emails, list):
            raise ValueError('recipientsIds and recipientsEmails must be lists.')

    except (KeyError, TypeError, json.JSONDecodeError, ValueError) as e:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Missing or invalid input: {e}'})
        }

    # Use a set to automatically handle duplicate emails
    final_email_set = set(email.lower() for email in loose_emails)

    # --- Fetch emails for the provided friend IDs ---
    if recipient_ids:
        try:
            keys_to_get = [{'UserId': uid} for uid in recipient_ids]
            if keys_to_get: # Only run batch_get if there are keys
                response = dynamodb.batch_get_item(
                    RequestItems={USERS_TABLE_NAME: {'Keys': keys_to_get}}
                )
                users_found = response.get('Responses', {}).get(USERS_TABLE_NAME, [])
                for user_item in users_found:
                    if 'Email' in user_item:
                        final_email_set.add(user_item['Email'].lower())
        except ClientError as e:
            err_msg = e.response.get('Error', {}).get('Message', str(e))
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Failed to retrieve recipients: {err_msg}'})
            }
            
    if not final_email_set:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'A group must contain at least one recipient.'})
        }

    # --- Assemble and persist the new mailing list ---
    list_id = str(uuid.uuid4())
    ml_item = {
        'ListId': list_id,
        'InitiatorId': initiator_id,
        'ListName': list_name,
        # CORRECTED: This now saves a simple list of email strings
        'RecipientsEmails': list(final_email_set) 
    }
    ml_table = dynamodb.Table(MAILING_LISTS_TABLE_NAME)
    
    try:
        ml_table.put_item(Item=ml_item)
    except ClientError as e:
        err_msg = e.response.get('Error', {}).get('Message', str(e))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Failed to create mailing list: {err_msg}'})
        }

    # --- Return HTTP 201 Created with the new ListId ---
    return {
        'statusCode': 201,
        'headers': cors_headers,
        'body': json.dumps({'ListId': list_id, 'RecipientsCount': len(final_email_set)})
    }

