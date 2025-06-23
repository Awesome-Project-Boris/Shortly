import json
import os
import boto3
from botocore.exceptions import ClientError

# Initialize the S3 client
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Deletes an object from an S3 bucket.
    This is used as a rollback mechanism if a profile update fails after
    an image has already been uploaded.

    Expects a JSON body with:
    - key (string): The key (filename) of the object to delete.
    """

    # --- Configuration ---
    bucket_name = os.environ.get('UPLOAD_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("UPLOAD_BUCKET_NAME environment variable is not set.")

    # CORS headers for the response
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,DELETE"
    }

    try:
        # Load the key from the request body
        body = json.loads(event.get('body', '{}'))
        key_to_delete = body.get('key')

        if not key_to_delete:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Missing "key" in request body.'})
            }

        # Delete the object from the S3 bucket
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=key_to_delete
        )

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': f"Object '{key_to_delete}' deleted successfully."})
        }

    except ClientError as e:
        print(f"Boto3 ClientError: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'An error occurred during S3 object deletion.'})
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'An unexpected server error occurred.'})
        }
