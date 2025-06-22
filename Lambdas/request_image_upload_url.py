import json
import boto3
import uuid
import os
from botocore.exceptions import ClientError

# Initialize the S3 client
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Generates a pre-signed S3 URL for securely uploading a file.
    The client sends a content type, and this function returns a URL
    that can be used to PUT the file directly into the S3 bucket.

    Expects a JSON body with:
    - contentType (string): The MIME type of the file (e.g., 'image/jpeg').
    """
    
    # --- Configuration ---
    # Fetch the bucket name from an environment variable for security and flexibility.
    # You must set this environment variable in your Lambda configuration.
    bucket_name = os.environ.get('UPLOAD_BUCKET_NAME')
    if not bucket_name:
        # Fails loudly if the bucket name is not configured
        raise ValueError("UPLOAD_BUCKET_NAME environment variable is not set.")

    # CORS headers for the response
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }
    
    try:
        # Load the content type from the request body
        body = json.loads(event.get('body', '{}'))
        content_type = body.get('contentType')

        if not content_type:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Missing "contentType" in request body.'})
            }

        # Generate a unique filename using a UUID to prevent overwrites
        # This key will be the name of the file in your S3 bucket.
        file_key = f"profile-pictures/{uuid.uuid4()}"

        # Generate the pre-signed URL for the upload operation
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_key,
                'ContentType': content_type
            },
            ExpiresIn=300  # The URL will be valid for 5 minutes (300 seconds)
        )
        
        # This is the public URL the image will have AFTER it has been uploaded.
        # You will store this URL in your DynamoDB User table.
        final_url = f"https://{bucket_name}.s3.amazonaws.com/{file_key}"

        # Return the pre-signed URL, the file key, and the final public URL
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'uploadUrl': presigned_url,
                'key': file_key,
                'finalUrl': final_url
            })
        }

    except ClientError as e:
        print(f"Boto3 ClientError: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'An error occurred while generating the upload URL.'})
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'An unexpected server error occurred.'})
        }
