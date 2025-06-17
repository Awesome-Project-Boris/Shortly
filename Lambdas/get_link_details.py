import json
import boto3
import os
from collections import Counter
from botocore.exceptions import ClientError

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')

# Use environment variables for table names
LINKS_TABLE_NAME = os.environ.get('LINKS_TABLE_NAME', 'Links')
LINK_CLICKS_TABLE_NAME = os.environ.get('LINK_CLICKS_TABLE_NAME', 'LinkClicks') # Assumed table for analytics

def lambda_handler(event, context):
    """
    Fetches comprehensive details for a given link, including its properties
    and aggregated click statistics by country.

    Expects a JSON body with 'linkId'.
    """
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    try:
        body = json.loads(event.get('body', '{}'))
        link_id = body.get('linkId')

        if not link_id:
            return {'statusCode': 400, 'headers': cors_headers, 'body': json.dumps({'message': 'Missing "linkId" in request body.'})}

        links_table = dynamodb.Table(LINKS_TABLE_NAME)
        
        # --- Step 1: Get the main link data ---
        link_response = links_table.get_item(Key={'LinkId': link_id})
        if 'Item' not in link_response:
            return {'statusCode': 404, 'headers': cors_headers, 'body': json.dumps({'message': 'Link not found.'})}
        
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
        # Convert Decimal types from DynamoDB to standard Python types for JSON serialization
        response_body = {
            'IsPrivate': bool(link_details.get('IsPrivate', False)),
            'IsPasswordProtected': bool(link_details.get('IsPasswordProtected', False)),
            'Password': link_details.get('Password'),
            'TotalClicks': int(link_details.get('NumberOfClicks', 0)),
            'clicksByCountry': dict(clicks_by_country) # Convert Counter to a regular dict
        }

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(response_body)
        }

    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'An unexpected server error occurred.'})}
