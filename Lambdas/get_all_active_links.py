import os  # for environment variables
import json  # for JSON parsing and serialization
import boto3  # AWS SDK for Python
import decimal  # to handle DynamoDB Decimal types
from boto3.dynamodb.conditions import Attr  # for building filter expressions

# Initialize DynamoDB resource (uses IAM role or AWS credentials)
dynamodb = boto3.resource('dynamodb')
# Table name configurable via environment variable (default: 'Links')
TABLE_NAME = os.environ.get('LINKS_TABLE', 'Links')


def _decimal_default(obj):
    """
    JSON serializer helper for DynamoDB Decimal objects.
    Converts whole-number Decimals to int, fractional to float.
    """
    if isinstance(obj, decimal.Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def lambda_handler(event, context):
    """
    AWS Lambda entry point: returns all links that are public and active.

    - Public links: IsPrivate == False
    - Active links: IsActive == True

    Scans the Links table with both filters applied.
    """
    table = dynamodb.Table(TABLE_NAME)
    try:
        # Apply filter for public (not private) and active links
        response = table.scan(
            FilterExpression=(
                Attr('IsActive').eq(True)
            )
        )
        links = response.get('Items', [])
    except Exception as e:
        # Return 500 if scan fails
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error fetching links: {e}'})
        }

    # Serialize and return filtered links
    return {
        'statusCode': 200,
        'body': json.dumps({'links': links}, default=_decimal_default)
    }
# Create mock event
# mock_event = {}

# # Call lambda handler with mock event
# result = lambda_handler(mock_event, None)

# # Print result
# print(json.dumps(result, indent=2))
