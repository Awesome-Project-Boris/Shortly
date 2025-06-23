import os
import json
import boto3
import decimal
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# --- Initialize DynamoDB and Table Resource ---
# It's a best practice to use an environment variable for the table name.
USERS_TABLE_NAME = os.environ.get('USERS_TABLE', 'Users')
dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USERS_TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    """
    Helper class to convert DynamoDB Decimal types to JSON-compatible int/float.
    """
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super(DecimalEncoder, self).default(o)

def lambda_handler(event, context):
    """
    Scans the Users table to retrieve a list of all active users, including a
    count of their links.
    
    Returns:
      200: A list of user objects.
      500: An error message if the scan fails.
    """
    try:
        # Use a FilterExpression to only get items where 'IsActive' is true.
        # Use a ProjectionExpression to only retrieve the needed attributes.
        # This is more efficient as it reduces the amount of data read from the table.
        response = users_table.scan(
            FilterExpression=Attr('IsActive').eq(True),
            ProjectionExpression="UserId, Username, Picture, Links"
        )
        
        users = response.get('Items', [])
        
        # The Scan operation has a 1MB limit per request. If the table is large,
        # we need to handle pagination to get all results.
        while 'LastEvaluatedKey' in response:
            response = users_table.scan(
                FilterExpression=Attr('IsActive').eq(True),
                ProjectionExpression="UserId, Username, Picture, Links",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            users.extend(response.get('Items', []))

        # Process the results to add LinkCount and remove the Links list.
        processed_users = []
        for user in users:
            # Calculate the number of links from the length of the 'Links' list.
            # The 'Links' attribute might not exist if the user has no links.
            link_count = len(user.get('Links', []))
            
            processed_users.append({
                'UserId': user['UserId'],
                'Username': user['Username'],
                'Picture': user.get('Picture'), # Use .get() for safety if Picture is optional
                'LinkCount': link_count
            })

        # Return the processed list of users
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # CORS header
            },
            'body': json.dumps(processed_users, cls=DecimalEncoder)
        }

    except ClientError as e:
        print(f"An error occurred: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Could not retrieve users from the database.'})
        }

