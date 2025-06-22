import os  # for reading environment variables
import json  # for parsing and serializing JSON
import uuid  # for generating unique identifiers
import boto3  # AWS SDK for Python (Boto3)
from botocore.exceptions import ClientError  # to catch DynamoDB-specific errors

# --- Initialize DynamoDB resource ---
# Uses IAM role or environment-based AWS credentials
dynamodb = boto3.resource('dynamodb')
# Table names can be overridden via Lambda environment variables
MAILING_LIST_TABLE = os.environ.get('MAILING_LIST_TABLE', 'Mailing_Lists')
USERS_TABLE = os.environ.get('USERS_TABLE', 'Users')


def lambda_handler(event, context):
    """
    AWS Lambda function to create a new mailing list.

    Expected JSON body parameters:
      - UserId (string): initiator of the mailing list
      - RecipientIds (list of strings): UserIds to include as recipients
      - ListName (string, optional): descriptive name for the list

    Workflow:
      1. Parse and validate input JSON
      2. Lookup each recipient's email in the Users table
      3. Generate a unique ListId
      4. Assemble the mailing-list item
      5. Persist to the MailingList table
      6. Return success or appropriate error response
    """
    # --- 1. Parse and validate input JSON ---
    try:
        raw_body = event.get('body', {})
        # API Gateway may pass body as a JSON string or already-parsed dict
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

        # Required parameters
        initiator_id = body['UserId']
        recipient_ids = body['RecipientIds']
        # Optional parameter with default
        list_name = body.get('ListName', '')

        # Validate that RecipientIds is indeed a list
        if not isinstance(recipient_ids, list):
            raise ValueError('RecipientIds must be a list of user IDs')

    except (KeyError, TypeError, json.JSONDecodeError, ValueError) as e:
        # Return HTTP 400 Bad Request for missing or invalid input
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing or invalid input: {e}'})
        }

    # Reference the Users table for email lookups
    users_table = dynamodb.Table(USERS_TABLE)
    recipients = []  # will hold valid recipient {UserId, Email} dicts

    # --- 2. Fetch each recipient's email ---
    for uid in recipient_ids:
        try:
            # Retrieve user record by primary key UserId
            resp = users_table.get_item(Key={'UserId': uid})
            user_item = resp.get('Item')
            # Only include if record exists and has an Email attribute
            if user_item and 'Email' in user_item:
                recipients.append({'UserId': uid, 'Email': user_item['Email']})
        except ClientError:
            # Skip this UID on any DynamoDB error (e.g., permissions)
            continue

    # --- 3. Generate unique mailing-list ID ---
    list_id = str(uuid.uuid4())  # UUID ensures low collision risk

    # --- 4. Assemble the DynamoDB item ---
    ml_item = {
        'ListId': list_id,
        'InitiatorId': initiator_id,
        'ListName': list_name,
        'RecipientsEmails': recipients  # list of {'UserId', 'Email'}
    }

    # --- 5. Persist the new mailing list to DynamoDB ---
    ml_table = dynamodb.Table(MAILING_LIST_TABLE)
    try:
        ml_table.put_item(Item=ml_item)
    except ClientError as e:
        # Return HTTP 500 if DynamoDB write fails
        err_msg = e.response.get('Error', {}).get('Message', str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to create mailing list: {err_msg}'})
        }

    # --- 6. Return HTTP 201 Created with details ---
    return {
        'statusCode': 201,
        'body': json.dumps({'ListId': list_id, 'RecipientsCount': len(recipients)})
    }
        
# Create a mock event with test data
# test_event = {
#     'body': {
#         'UserId': 'Allie1',
#         'RecipientIds': ['d4', 'Chuck3'],
#         'ListName': 'Test Mailing List'
#     }
# }

# # Call the lambda handler with the test event
# result = lambda_handler(test_event, None)

# # Print the result
# print(json.dumps(result, indent=2))