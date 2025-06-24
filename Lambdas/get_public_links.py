import os
import json
import boto3
from boto3.dynamodb.conditions import Attr

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
# Table name from environment variable
TABLE_NAME = os.environ.get('LINKS_TABLE', 'Links')

def lambda_handler(event, context):
    """
    Lambda entry point: returns a projected list of public and active links.

    Public links: IsPrivate == False
    Active links: IsActive == True
    """
    
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,GET,POST' # Allow POST for body requests
    }
    
    table = dynamodb.Table(TABLE_NAME)
    try:
        # Scan for links that are both public and active
        response = table.scan(
            # This expression filters for the desired items on the server side
            FilterExpression=(
                Attr('IsPrivate').eq(False) & Attr('IsActive').eq(True)
            ),
            # NEW: This expression tells DynamoDB to only return these specific attributes
            # This is highly efficient and reduces the amount of data read and transferred.
            ProjectionExpression="LinkId, #nm, Description, IsPasswordProtected, ownerId, #str",
            # We use ExpressionAttributeNames because 'Name' and 'String' are reserved words in DynamoDB
            ExpressionAttributeNames={
                "#nm": "Name",
                "#str": "String"
            }
        )
        links = response.get('Items', [])
        
    except ClientError as e:
        print(f"Error fetching links: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Error fetching links from the database.'})
        }

    # Return the filtered and projected list of links
    return {
        'statusCode': 200,
        'headers': cors_headers,
        # The response body now contains a list of link objects
        'body': json.dumps(links)
    }
