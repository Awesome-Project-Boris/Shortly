#!/bin/bash

# Bash script to download all files from an AWS S3 bucket.

# --- Configuration ---
# TODO: Replace with your S3 bucket name.
S3_BUCKET_NAME="shortly-rlt"

# TODO: Replace with the local directory path where you want to save the files.
# The script will create this directory if it doesn't exist.
LOCAL_DIRECTORY="./s3-downloads"


# --- Script Logic ---

# Check if the AWS CLI is installed.
if ! command -v aws &> /dev/null
then
    echo "Error: AWS CLI could not be found."
    echo "Please install it and configure your credentials."
    echo "Installation guide: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check if a bucket name has been provided.
if [ "$S3_BUCKET_NAME" == "your-s3-bucket-name" ]; then
    echo "Error: Please edit this script and set the S3_BUCKET_NAME variable."
    exit 1
fi

# Create the local directory if it doesn't already exist.
echo "Creating local directory if it doesn't exist: ${LOCAL_DIRECTORY}"
mkdir -p "$LOCAL_DIRECTORY"

# Construct the S3 URI.
S3_URI="s3://${S3_BUCKET_NAME}"

# Announce the start of the download.
echo "--------------------------------------------------"
echo "Starting download from S3 bucket: ${S3_BUCKET_NAME}"
echo "Saving files to local directory: ${LOCAL_DIRECTORY}"
echo "--------------------------------------------------"

# Use the AWS S3 sync command to download files.
# The `sync` command recursively copies new and updated files from the source to the destination.
# It's more efficient than `cp` for downloading a large number of files.
aws s3 sync "$S3_URI" "$LOCAL_DIRECTORY"

# Check the exit code of the sync command.
SYNC_STATUS=$?
if [ $SYNC_STATUS -eq 0 ]; then
    echo "--------------------------------------------------"
    echo "✅ Success! All files have been downloaded."
    echo "--------------------------------------------------"
else
    echo "--------------------------------------------------"
    echo "❌ Error: The download process failed with exit code ${SYNC_STATUS}."
    echo "Check the error messages above for details."
    echo "Ensure your AWS credentials are correct and you have permissions for the bucket."
    echo "--------------------------------------------------"
fi

exit $SYNC_STATUS
