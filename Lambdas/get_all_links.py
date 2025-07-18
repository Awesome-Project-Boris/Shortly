import os
import json
import boto3
import decimal
from boto3.dynamodb.conditions import Attr

# Initialize DynamoDB resource using IAM role or AWS creds

dynamodb = boto3.resource('dynamodb')
# Table name configured via environment variable (default: 'Links')
TABLE_NAME = 'Links'


def _decimal_default(obj):
    """Helper to convert DynamoDB Decimal objects to JSON-serializable types."""
    if isinstance(obj, decimal.Decimal):
        # If no fractional part, output as int
        if obj % 1 == 0:
            return int(obj)
        # Otherwise output as float
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def lambda_handler(event, context):
    """
    Lambda entry point: returns all public links (IsPrivate == False).
    Scans the table with a filter and returns matching items.
    """
    table = dynamodb.Table(TABLE_NAME)
    try:
        # Scan for items where IsPrivate attribute is False
        response = table.scan()
        links = response.get('Items', [])
    except Exception as e:
        # Return 500 if the scan operation fails
        return {
            'statusCode': 500,
                    "headers": {"Content-Type": "application/json",
                    'Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                    'Access-Control-Allow-Origin': "*"
                    },
            'body': json.dumps({'error': f'Error fetching public links: {e}'})
        }

    # Return the list of public links, converting any Decimal types
    return {
        'statusCode': 200,
                "headers": {"Content-Type": "application/json",
                    'Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                    'Access-Control-Allow-Origin': "*"
                    },
        'body': json.dumps({'links': links}, default=_decimal_default)
    }

# Create mock event
# mock_event = {}

# # Call lambda handler with mock event and None for context
# response = lambda_handler(mock_event, None)

# # Print response
# print(json.dumps(response, indent=2))