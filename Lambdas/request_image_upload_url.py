import json
import boto3
import uuid
import os
from botocore.exceptions import ClientError

# Initialize the S3 client
s3_client = boto3.client('s3')

def _make_response(status_code, body):
    """
    Centralized function to create API responses with full CORS headers.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            # MODIFIED: Added more allowed methods for maximum compatibility
            'Access-Control-Allow-Methods': 'OPTIONS,POST,PUT,DELETE'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    """
    Generates a pre-signed S3 URL for securely uploading a file,
    with robust CORS handling.
    """
    
    # --- CORS Preflight Handling ---
    # This block handles the browser's initial OPTIONS request,
    # which is essential for CORS to work correctly.
    if event.get('httpMethod') == 'OPTIONS':
        return _make_response(204, {})

    # --- Configuration ---
    bucket_name = os.environ.get('UPLOAD_BUCKET_NAME')
    if not bucket_name:
        # Fails loudly if the bucket name is not configured
        print("CRITICAL ERROR: UPLOAD_BUCKET_NAME environment variable is not set.")
        return _make_response(500, {'message': 'Server configuration error: Missing bucket name.'})

    try:
        # Load the content type from the request body
        body = json.loads(event.get('body', '{}'))
        content_type = body.get('contentType')

        if not content_type:
            return _make_response(400, {'message': 'Missing "contentType" in request body.'})

        # Generate a unique filename using a UUID to prevent overwrites
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
        return _make_response(200, {
            'uploadUrl': presigned_url,
            'key': file_key,
            'finalUrl': final_url
        })

    except ClientError as e:
        print(f"Boto3 ClientError: {e}")
        return _make_response(500, {'message': 'An error occurred while generating the upload URL.'})
    except Exception as e:
        print(f"Error: {e}")
        return _make_response(500, {'message': 'An unexpected server error occurred.'})
