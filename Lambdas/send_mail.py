import os
import smtplib
import json
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Environment variables
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SENDER_EMAIL = os.environ['GMAIL_ADDRESS']
SENDER_PASSWORD = os.environ['GMAIL_PASSWORD']
MAILING_LIST_TABLE = os.environ.get('MAILING_LIST_TABLE', 'Mailing_Lists')  # DynamoDB table name for mailing lists

# Initialize DynamoDB client for mailing list lookup
dynamodb = boto3.resource('dynamodb')
mailing_table = dynamodb.Table(MAILING_LIST_TABLE)


def lambda_handler(event, context):
    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return _response(400, {'error': 'Invalid JSON in request body.'})

    subject = body.get('subject', '')
    mail_body = body.get('mail_body', '')

    # Determine recipients: single or mailing list
    recipients = []
    if 'list_id' in body:
        list_id = body['list_id']
        # Fetch mailing list from DynamoDB
        resp = mailing_table.get_item(Key={'ListId': list_id})
        item = resp.get('Item')
        if not item or 'RecipientsEmails' not in item:
            return _response(404, {'error': f'Mailing list {list_id} not found.'})
        recipients = item['RecipientsEmails']
    elif 'recipient_email' in body:
        recipients = [body['recipient_email']]
    else:
        return _response(400, {'error': 'Provide recipient_email or list_id in request body.'})

    # Prepare SMTP connection
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
    except Exception as e:
        return _response(500, {'error': f'Failed to connect to SMTP server: {e}'})

    send_errors = []
    # Send email to each recipient
    for recipient in recipients:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(mail_body, 'plain'))
        try:
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
        except Exception as e:
            send_errors.append({'recipient': recipient, 'error': str(e)})

    server.quit()

    if send_errors:
        return _response(207, {'message': 'Some emails failed', 'errors': send_errors})
    return _response(200, {'message': f'Email sent successfully to {len(recipients)} recipient(s).'})


def _response(status_code, body_dict):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
        'body': json.dumps(body_dict)
    }

# Create mock event for testing
# mock_event = {
#     "body": json.dumps({
#         "subject": "Test Email",
#         "mail_body": "This is a test email body",
#         "recipient_email": "liormasturov@gmail.com"
#     })
# }

# # Call lambda handler with mock event
# result = lambda_handler(mock_event, None)