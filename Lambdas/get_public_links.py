import os
import json
import boto3
import decimal
from boto3.dynamodb.conditions import Attr

# Initialize DynamoDB resource using IAM role or AWS creds

dynamodb = boto3.resource('dynamodb')
# Table name configured via environment variable (default: 'Links')
TABLE_NAME = os.environ.get('LINKS_TABLE', 'Links')


def _decimal_default(obj):
    """Helper to convert DynamoDB Decimal objects to JSON-serializable types."""
    if isinstance(obj, decimal.Decimal):
        # Convert whole numbers to int
        if obj % 1 == 0:
            return int(obj)
        # Preserve decimals as float
        return float(obj)
    # Let other types fail loudly
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def lambda_handler(event, context):
    """
    Lambda entry point: returns all public and active links.

    Public links: IsPrivate == False
    Active links: IsActive == True
    Performs a table scan with both filters applied.
    """
    table = dynamodb.Table(TABLE_NAME)
    try:
        # Scan for links that are both public and active
        response = table.scan(
            FilterExpression=(
                Attr('IsPrivate').eq(False) & Attr('IsActive').eq(True)
            )
        )
        links = response.get('Items', [])
    except Exception as e:
        # Return 500 if the scan operation fails
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error fetching links: {e}'})
        }

    # Return filtered links, converting any Decimal types
    return {
        'statusCode': 200,
        'body': json.dumps({'links': links}, default=_decimal_default)
    }
