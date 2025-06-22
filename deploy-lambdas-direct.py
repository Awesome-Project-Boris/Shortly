#!/usr/bin/env python3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# This script deploys all Lambda functions in the ./lambda directory directly
# without modifying code or adding any environment prefix.
# Usage: python3 deploy-lambda-direct.py

def aws_cli_exists(function_name: str) -> bool:
    """
    Check if a Lambda function exists by name.
    """
    try:
        subprocess.run(
            ['aws', 'lambda', 'get-function', '--function-name', function_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def zip_lambda(file_path: Path) -> Path:
    """
    Package a single .py file into a zip suitable for Lambda deployment.
    The lambda handler will be <filename>.lambda_handler.
    """
    zip_path = Path(tempfile.gettempdir()) / f"{file_path.stem}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(file_path, arcname=file_path.name)
    return zip_path


def deploy_lambda(zip_path: Path, function_name: str, role_arn: str):
    """
    Deploys (creates or updates) a Lambda function using AWS CLI.
    """
    if aws_cli_exists(function_name):
        print(f"• Lambda exists. Updating code for {function_name}")
        subprocess.run(
            ['aws', 'lambda', 'update-function-code',
             '--function-name', function_name,
             '--zip-file', f"fileb://{zip_path}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        print(f"✓ Updated code for {function_name}")
    else:
        print(f"• Lambda does not exist. Creating {function_name}")
        subprocess.run(
            ['aws', 'lambda', 'create-function',
             '--function-name', function_name,
             '--runtime', 'python3.13',
             '--role', role_arn,
             '--handler', f"{function_name}.lambda_handler",
             '--zip-file', f"fileb://{zip_path}",
             '--timeout', '15',
             '--memory-size', '128',
             '--architecture', 'x86_64',
             '--publish'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        print(f"✓ Created {function_name}")


def main():
    # Determine AWS account and default role ARN
    try:
        account_id = subprocess.run(
            ['aws', 'sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True
        ).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Unable to get AWS account ID: {e}", file=sys.stderr)
        sys.exit(1)

    role_arn = f"arn:aws:iam::{account_id}:role/LabRole"
    print(f"Using IAM role: {role_arn}")

    # Locate lambda directory
    lambda_dir = Path.cwd() / 'Lambdas'
    if not lambda_dir.is_dir():
        print(f"❌ Lambda directory not found at {lambda_dir}", file=sys.stderr)
        sys.exit(1)

    # Iterate over each .py file and deploy
    for file_path in lambda_dir.glob('*.py'):
        fn_name = file_path.stem
        print(f"\nPackaging function: {fn_name}")
        zip_path = zip_lambda(file_path)
        print(f"• Zipped {file_path.name} → {zip_path}")
        deploy_lambda(zip_path, fn_name, role_arn)
        zip_path.unlink(missing_ok=True)

    print("\n✅ All Lambdas deployed.")


if __name__ == '__main__':
    main()
