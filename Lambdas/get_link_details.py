import json
import boto3
import os
from collections import Counter
from botocore.exceptions import ClientError
import decimal

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Use environment variables for table names
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
LINK_CLICKS_TABLE_NAME = os.environ.get('LINK_CLICKS_TABLE_NAME', 'LinkClicks')

# Helper for JSON serialization of DynamoDB's Decimal type
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super(DecimalEncoder, self).default(o)

def _make_response(status_code, body):
    """
    Centralized function to create API responses with full CORS headers.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }

def lambda_handler(event, context):
    """
    Fetches comprehensive details for a given link, including its properties
    and aggregated click statistics by country.
    """
    
    # Handle CORS preflight request
    if event.get('httpMethod') == 'OPTIONS':
        return _make_response(204, {})

    try:
        body = json.loads(event.get('body', '{}'))
        link_id = body.get('linkId')

        if not link_id:
            return _make_response(400, {'message': 'Missing "linkId" in request body.'})

        links_table = dynamodb.Table(LINKS_TABLE_NAME)
        
        # --- Step 1: Get the main link data ---
        link_response = links_table.get_item(Key={'LinkId': link_id})
        if 'Item' not in link_response:
            return _make_response(404, {'message': 'Link not found.'})
        
        link_details = link_response['Item']
        
        # --- Step 2: Get and aggregate click data by country ---
        clicks_by_country = {}
        try:
            clicks_table = dynamodb.Table(LINK_CLICKS_TABLE_NAME)
            # Query all clicks for the given LinkId. This assumes LinkId is a GSI partition key for efficient querying.
            click_response = clicks_table.query(
                IndexName='LinkId-index', # Assumed GSI for querying by LinkId
                KeyConditionExpression=boto3.dynamodb.conditions.Key('LinkId').eq(link_id)
            )
            
            # Use collections.Counter for a highly efficient way to count occurrences
            country_list = [item['Country'] for item in click_response.get('Items', []) if 'Country' in item]
            clicks_by_country = Counter(country_list)

        except ClientError as e:
            # It's okay if the LinkClicks table or index doesn't exist yet, we just return empty stats.
            print(f"Could not fetch click analytics (this may be normal): {e}")
            clicks_by_country = {}

        # --- Step 3: Combine all data into a single response ---
        response_body = {
            'IsPrivate': bool(link_details.get('IsPrivate', False)),
            'IsPasswordProtected': bool(link_details.get('IsPasswordProtected', False)),
            'Password': link_details.get('Password'),
            'TotalClicks': int(link_details.get('NumberOfClicks', 0)),
            'clicksByCountry': dict(clicks_by_country) # Convert Counter to a regular dict
        }

        return _make_response(200, response_body)

    except Exception as e:
        print(f"Error: {e}")
        return _make_response(500, {'message': 'An unexpected server error occurred.'})

