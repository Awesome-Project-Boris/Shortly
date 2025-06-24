import boto3
import json
from boto3.dynamodb.conditions import Key

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
USERS_TABLE = 'Users'
LINKS_TABLE = 'Links'
USER_LINKS_INDEX = 'UserId-index'

users_table = dynamodb.Table(USERS_TABLE)
links_table = dynamodb.Table(LINKS_TABLE)

def lambda_handler(event, context):
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': ''
        }

    # Parse request body instead of query parameters
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'message': 'Invalid JSON in request body'})
        }

    user_id = body.get('userId')

    # Fetch all users
    try:
        users_response = users_table.scan()
        users = users_response.get('Items', [])
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'message': f'Error scanning users: {str(e)}'})
        }

    # Fetch links for the given user
    links = []
    if user_id:
        try:
            resp = links_table.query(
                IndexName=USER_LINKS_INDEX,
                KeyConditionExpression=Key('UserId').eq(user_id)
            )
            links = resp.get('Items', [])
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'message': f'Error querying links: {str(e)}'})
            }

    # Map user data
    users_data = [
        {
            'userId': u.get('UserId', ''),
            'userName': u.get('Username', ''),
            'fullName': u.get('FullName', ''),
            'country': u.get('Country', ''),
            'dateJoined': u.get('DateJoined', ''),
            'totalClicks': u.get('NumberOfClicks', 0),
            'active': u.get('IsActive', False)
        }
        for u in users
    ]

    # Map link data
    links_data = [
        {
            'linkName': l.get('Name', ''),
            'description': l.get('Description', ''),
            'link': l.get('String', ''),
            'publicPrivate': l.get('IsPrivate', False),
            'hasPassword': l.get('IsPasswordProtected', False),
            'active': l.get('IsActive', False)
        }
        for l in links
    ]

    response_body = {
        'users': users_data,
        'links': links_data
    }

    return {
        'statusCode': 200,
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(response_body)
    }

# Create mock event with test data
# mock_event = {
#     "httpMethod": "POST",
#     "body": json.dumps({
#         "userId": "894980c8-e8a6-4921-9bb0-f917671caa65"
#     })
# }

# # Call lambda handler with mock event
# response = lambda_handler(mock_event, None)
# print(response)