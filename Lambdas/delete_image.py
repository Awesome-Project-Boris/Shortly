import json
import boto3
import os
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Note: the image name has to match the name in the S3 bucket.




# Environment variables
# bucket_name = os.environ.get('UPLOAD_BUCKET_NAME') # If we wanted to use a variable for bucket name, we would use this line
users_table = dynamodb.Table(os.environ.get('USERS_TABLE_NAME', 'Users'))


def get_single_bucket_name():
    s3 = boto3.client('s3')
    buckets = s3.list_buckets().get("Buckets", [])
    if len(buckets) != 1:
        raise ValueError(f"Expected 1 bucket, found {len(buckets)}.")
    return buckets[0]['Name']

bucket_name = get_single_bucket_name()



def lambda_handler(event, context):
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,DELETE"
    }

    try:
        body = json.loads(event.get('body', '{}'))
        key_to_delete = body.get('key')
        user_id = body.get('UserId')

        if not key_to_delete or not user_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Missing "key" or "UserId" in request body.'})
            }

        
        
        # debugging output
        # msg = f"Attempting to delete S3 object '{key_to_delete}' from bucket '{bucket_name}'"
        # print(msg)

        # return {
        #     'statusCode': 200,
        #     'headers': cors_headers,
        #     'body': json.dumps({'message': msg})
        # }
                
        
        
        
        
        # Step 1: Delete object from S3
        s3_client.delete_object(Bucket=bucket_name, Key=key_to_delete)

        # Step 2: Fetch user
        user_data = users_table.get_item(Key={"UserId": user_id}).get("Item")
        if not user_data:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'message': f"User '{user_id}' not found."})
            }


        # Step 3: Clear profile Picture if it matches the deleted key
        current_url = user_data.get("Picture", "")
        if current_url and key_to_delete in current_url:
            users_table.update_item(
                Key={"UserId": user_id},
                UpdateExpression="SET Picture = :p",
                ExpressionAttributeValues={":p": ""}
            )

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': f"Image '{key_to_delete}' deleted and user profile updated."})
        }

    except ClientError as e:
        print(f"Boto3 ClientError: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'Error deleting image from S3 or updating DynamoDB.'})
        }
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'message': 'An unexpected server error occurred.'})
        }
