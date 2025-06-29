import json
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('Users')  # Change if your table name is dynamic

def lambda_handler(event, context):
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,GET"
    }

    try:
        # Scan for users where IsActive == true (boolean, not string)
        response = users_table.scan(
            FilterExpression=Attr('IsActive').eq(True)
        )

        active_users = response.get("Items", [])

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'users': active_users})
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'An unexpected error occurred.'})
        }
