import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize DynamoDB and S3 clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Fetch table and bucket names from environment variables
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'Users')
UPLOAD_BUCKET_NAME = os.environ.get('UPLOAD_BUCKET_NAME')

def lambda_handler(event, context):
    """
    Updates a user's profile in DynamoDB. If a new picture is provided,
    this function also deletes the old picture from the S3 bucket after
    a successful database update.
    
    Expects a JSON body with:
    - userId (string): The ID of the user to update.
    - updateData (dict): A dictionary with fields to update (e.g., {'FullName': 'new name'}).
    - oldPictureKey (string, optional): The S3 key of the old picture to be deleted.
    """

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,PUT"
    }

    try:
        if not UPLOAD_BUCKET_NAME:
            raise ValueError("UPLOAD_BUCKET_NAME environment variable is not set.")

        body = json.loads(event.get('body', '{}'))
        user_id = body.get('userId')
        update_data = body.get('updateData')
        old_picture_key = body.get('oldPictureKey')

        if not user_id or not update_data:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Missing userId or updateData in request body.'})
            }

        table = dynamodb.Table(USERS_TABLE_NAME)

        # --- Construct DynamoDB Update Expression ---
        # This dynamically builds the update expression based on the keys in updateData
        update_expression_parts = []
        expression_attribute_values = {}
        for key, value in update_data.items():
            # Use placeholders to avoid issues with reserved keywords
            update_expression_parts.append(f"#{key} = :{key}")
            expression_attribute_values[f":{key}"] = value
        
        # We need ExpressionAttributeNames because some keys might be reserved words
        expression_attribute_names = {f"#{key}": key for key in update_data.keys()}
        
        update_expression = "SET " + ", ".join(update_expression_parts)

        # --- Update DynamoDB Item ---
        table.update_item(
            Key={'UserId': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        # --- Cleanup: Delete Old S3 Object (if applicable) ---
        # This part runs only if the database update was successful AND an old key was provided.
        if old_picture_key:
            print(f"Database updated. Deleting old picture with key: {old_picture_key}")
            try:
                s3_client.delete_object(Bucket=UPLOAD_BUCKET_NAME, Key=old_picture_key)
                print("Old picture deleted successfully.")
            except ClientError as e:
                # Log the error, but don't fail the whole request since the main goal (DB update) succeeded.
                # You might want to add more robust monitoring here for cleanup failures.
                print(f"Error deleting old picture from S3: {e}")

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'User profile updated successfully.'})
        }

    except ClientError as e:
        print(f"DynamoDB ClientError: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'A database error occurred.'})}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'headers': cors_headers, 'body': json.dumps({'message': 'An unexpected server error occurred.'})}

