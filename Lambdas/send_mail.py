import os
import smtplib
import json
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from botocore.exceptions import ClientError

# --- AWS & Email Configuration (from Environment Variables) ---
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SENDER_EMAIL = os.environ['GMAIL_ADDRESS']
SENDER_PASSWORD = os.environ['GMAIL_PASSWORD']
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')
MAILING_LISTS_TABLE_NAME = os.environ.get('MAILING_LISTS_TABLE_NAME', 'Mailing_Lists')

# --- Initialize DynamoDB Resources ---
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE_NAME)
mailing_table = dynamodb.Table(MAILING_LISTS_TABLE_NAME)

def _response(status_code, body_dict):
    """Helper function to create a consistent API response with full CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
        'body': json.dumps(body_dict)
    }

def lambda_handler(event, context):
    """
    Receives a share request, compiles a unique list of recipient emails from
    multiple sources (groups, friends, direct), and sends each a custom email.
    """
    # 1. CORS Preflight Handling
    if event.get('httpMethod') == 'OPTIONS':
        return _response(204, {})

    try:
        body = json.loads(event.get('body', '{}'))
        sender_id = body.get('senderId')
        link_id = body.get('linkId')
        group_ids = body.get('groupIds', [])
        friend_ids = body.get('friendIds', [])
        recipients_emails = body.get('recipientsEmails', [])
        site_url = body.get('site')

        if not all([sender_id, link_id, site_url]):
            return _response(400, {'error': 'Missing required fields: senderId, linkId, or site.'})

    except json.JSONDecodeError:
        return _response(400, {'error': 'Invalid JSON in request body.'})
        
    final_recipients = set()
    
    # --- Data Aggregation ---
    try:
        # Requirement #4: Add loose emails to the set
        for email in recipients_emails:
            final_recipients.add(email.strip().lower())

        # Requirement #3: Process friend IDs to get their emails
        for friend_id in friend_ids:
            resp = users_table.get_item(Key={'UserId': friend_id})
            if 'Item' in resp and 'Email' in resp['Item']:
                final_recipients.add(resp['Item']['Email'].strip().lower())

        # Requirement #2: Process group IDs to get their member emails
        for group_id in group_ids:
            resp = mailing_table.get_item(Key={'ListId': group_id})
            if 'Item' in resp and 'RecipientsEmails' in resp['Item']:
                for email in resp['Item']['RecipientsEmails']:
                     final_recipients.add(email.strip().lower())
        
        # Fetch sender's username for the email subject
        sender_resp = users_table.get_item(Key={'UserId': sender_id})
        sender_username = sender_resp.get('Item', {}).get('Username', 'A friend')

    except ClientError as e:
        print(f"DynamoDB Error: {e}")
        return _response(500, {'error': 'A database error occurred while gathering recipients.'})

    if not final_recipients:
        return _response(400, {'error': 'No valid recipients found to send emails to.'})

    # --- Email Construction & Sending ---
    
    # Requirement #6: Construct personalized subject and body
    subject = f"{sender_username} from Shortly sent you a new link!"
    html_body = f"""
    <html>
      <body>
        <p>Hello,</p>
        <p>{sender_username} has shared a link with you. Click below to view:</p>
        <p><a href="{site_url}">{site_url}</a></p>
        <br>
        <p>Shared via Shortly.</p>
      </body>
    </html>
    """
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
    except Exception as e:
        return _response(500, {'error': f'Failed to connect to SMTP server: {e}'})

    # Requirement #1: Iterate through the unique list of recipients and send email
    send_errors = []
    for recipient in final_recipients:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html')) # Sending as HTML to make link clickable
        try:
            server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
        except Exception as e:
            send_errors.append({'recipient': recipient, 'error': str(e)})

    server.quit()

    if send_errors:
        return _response(207, {'message': 'Some emails failed to send.', 'errors': send_errors})
        
    return _response(200, {'message': f'Email sent successfully to {len(final_recipients)} unique recipient(s).'})


# Create mock event
mock_event = {
    "httpMethod": "POST",
    "body": json.dumps({
        "senderId": "user123",
        "linkId": "link456", 
        "groupIds": ["group1", "group2"],
        "friendIds": ["friend1", "friend2"],
        "recipientsEmails": ["roishm83@gmail.com", ],
        "site": "https://shortly.com/link456"
    })
}

# Call lambda handler with mock event
response = lambda_handler(mock_event, None)
print(response)