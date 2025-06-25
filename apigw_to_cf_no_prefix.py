#!/usr/bin/env python3
"""
Convert API Gateway export JSON into a CloudFormation YAML template,
with full CORS support and correct IAM role for Lambda integrations.
This version uses the original names for the API and functions, without any environment prefixes.
"""
import json
import yaml
import re
import argparse
from collections import OrderedDict
from datetime import datetime, timezone

# Helper to sanitize names for CloudFormation logical IDs
def sanitize_name(name):
    """Creates a CloudFormation-compliant logical ID from a given string."""
    # Split by any non-alphanumeric characters
    parts = re.split(r'[^0-9a-zA-Z]+', name)
    # Capitalize each part and join them together
    return ''.join([part.capitalize() for part in parts if part])

# Convert OrderedDict to plain dicts for YAML serialization
def ordered_to_plain(obj):
    """Recursively converts OrderedDicts to regular dicts for clean YAML output."""
    if isinstance(obj, OrderedDict):
        obj = dict(obj)
    if isinstance(obj, dict):
        return {k: ordered_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [ordered_to_plain(v) for v in obj]
    return obj

# Main conversion logic
def convert_api_to_cfn(api_json):
    """
    Takes an API Gateway definition in JSON format and converts it
    to a CloudFormation template in an OrderedDict.
    """
    template = OrderedDict()
    template['AWSTemplateFormatVersion'] = '2010-09-09'
    template['Description'] = f"CloudFormation template for API Gateway API: {api_json.get('name')}. Generated on {datetime.now(timezone.utc).isoformat()}"
    
    template['Parameters'] = {}

    resources = OrderedDict()
    
    # Create the main RestApi resource
    api_logical = sanitize_name(api_json['name'] + 'RestApi')
    resources[api_logical] = {
        'Type': 'AWS::ApiGateway::RestApi',
        'Properties': {
            'Name': api_json['name'],
            'EndpointConfiguration': {'Types': ['REGIONAL']}
        }
    }

    # Pre-populate a map of resource IDs to their generated logical IDs for easy reference
    id_map = {}
    root_id = None
    for res in api_json['resources']:
        if res['path'] == '/':
            root_id = res['id']
            id_map[res['id']] = None
        else:
            id_map[res['id']] = sanitize_name(api_json['name'] + res['path'].replace('/', '_') + 'Resource')

    method_logical_ids = []
    
    # MODIFICATION: Use a single, sorted loop to create resources and their methods together.
    # This ensures parent resources are defined before their children in the template, preventing deployment errors.
    for res in sorted(api_json['resources'], key=lambda x: x['path']):
        # Part 1: Create the AWS::ApiGateway::Resource object for the path
        if res['path'] != '/':
            logical_id = id_map[res['id']]
            parent_id = res.get('parentId')
            
            # Determine the parent resource reference
            if parent_id == root_id:
                parent_ref = {'Fn::GetAtt': [api_logical, 'RootResourceId']}
            else:
                # This Ref creates an implicit dependency on the parent resource
                parent_ref = {'Ref': id_map[parent_id]}
                
            resources[logical_id] = {
                'Type': 'AWS::ApiGateway::Resource',
                'Properties': {
                    'RestApiId': {'Ref': api_logical},
                    'ParentId': parent_ref,
                    'PathPart': res['pathPart']
                }
            }
        
        # Part 2: Create the AWS::ApiGateway::Method objects for this resource
        # Get a reference to the resource (either root or a created resource)
        res_ref = {'Fn::GetAtt': [api_logical, 'RootResourceId']} if res['path'] == '/' else {'Ref': id_map[res['id']]}
        
        # Get all HTTP methods for the current resource to correctly build CORS headers
        all_http_methods = list(res.get('resourceMethods', {}).keys())

        for http_method, method_def in res.get('resourceMethods', {}).items():
            method_log = sanitize_name(api_json['name'] + res['path'].replace('/', '_') + http_method + 'Method')
            method_logical_ids.append(method_log)
            
            req_params = {p: v for p, v in method_def.get('requestParameters', {}).items()}
            
            props = {
                'RestApiId': {'Ref': api_logical},
                'ResourceId': res_ref,
                'HttpMethod': http_method,
                'AuthorizationType': method_def.get('authorizationType', 'NONE'),
                'ApiKeyRequired': method_def.get('apiKeyRequired', False),
                'RequestParameters': req_params,
                'MethodResponses': [],
            }
            
            # Define Method Responses
            for status_code, response_def in method_def.get('methodResponses', {}).items():
                props['MethodResponses'].append({
                    'StatusCode': status_code,
                    'ResponseModels': response_def.get('responseModels', {}),
                    'ResponseParameters': {k: v for k, v in response_def.get('responseParameters', {}).items()}
                })

            # Define the Integration
            integ = method_def.get('methodIntegration', {})
            if integ:
                iobj = {'Type': integ['type']}
                raw_uri = integ.get('uri')

                # Handle AWS/AWS_PROXY integrations, typically for Lambda
                if integ['type'] in ['AWS', 'AWS_PROXY'] and raw_uri:
                    match = re.search(r'function:([^/]+)/invocations', raw_uri)
                    if match:
                        function_name = match.group(1)
                        iobj['Uri'] = {'Fn::Sub': (
                            f"arn:aws:apigateway:${{AWS::Region}}:lambda:path/2015-03-31/functions/arn:aws:lambda:${{AWS::Region}}:${{AWS::AccountId}}:function:{function_name}/invocations"
                        )}
                        iobj['IntegrationHttpMethod'] = integ.get('httpMethod', 'POST')
                        iobj['Credentials'] = {'Fn::Sub': 'arn:aws:iam::${AWS::AccountId}:role/LabRole'}
                    else:
                        iobj['Uri'] = raw_uri
                
                if integ.get('requestParameters'): iobj['RequestParameters'] = integ['requestParameters']
                if integ.get('requestTemplates'): iobj['RequestTemplates'] = integ['requestTemplates']
                if integ.get('passthroughBehavior'): iobj['PassthroughBehavior'] = integ['passthroughBehavior']
                
                iobj['IntegrationResponses'] = []
                for status_code, integ_response_def in integ.get('integrationResponses', {}).items():
                     iobj['IntegrationResponses'].append({
                        'StatusCode': status_code,
                        'ResponseParameters': {k: v for k, v in integ_response_def.get('responseParameters', {}).items()},
                        'ResponseTemplates': {k: v for k, v in integ_response_def.get('responseTemplates', {}).items() if v is not None}
                    })

                props['Integration'] = iobj

            resources[method_log] = {'Type': 'AWS::ApiGateway::Method', 'Properties': props}

        # Part 3: Add an OPTIONS method for CORS if any methods are defined on the resource
        if all_http_methods:
            opt_log = sanitize_name(api_json['name'] + res['path'].replace('/', '_') + 'OptionsMethod')
            method_logical_ids.append(opt_log)
            
            allowed_methods_str = f"'{','.join(sorted(all_http_methods))},OPTIONS'"
            
            cors_headers = {
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': allowed_methods_str,
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            }
            
            resources[opt_log] = {
                'Type': 'AWS::ApiGateway::Method',
                'Properties': {
                    'RestApiId': {'Ref': api_logical},
                    'ResourceId': res_ref,
                    'HttpMethod': 'OPTIONS',
                    'AuthorizationType': 'NONE',
                    'MethodResponses': [{
                        'StatusCode': '200',
                        'ResponseModels': {'application/json': 'Empty'},
                        'ResponseParameters': {k: False for k in cors_headers.keys()}
                    }],
                    'Integration': {
                        'Type': 'MOCK',
                        'RequestTemplates': {'application/json': '{"statusCode": 200}'},
                        'IntegrationResponses': [{
                            'StatusCode': '200',
                            'ResponseParameters': cors_headers,
                            'ResponseTemplates': {'application/json': ''}
                        }]
                    }
                }
            }

    # Create the Deployment resource, making its logical ID unique with a timestamp
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    deployment_log = sanitize_name(f"{api_json['name']}Deployment{timestamp}")
    resources[deployment_log] = {
        'Type': 'AWS::ApiGateway::Deployment',
        'DependsOn': sorted(list(set(method_logical_ids))),
        'Properties': {
            'RestApiId': {'Ref': api_logical}
        }
    }
    
    # Create an explicit Stage resource using the name from the input JSON.
    stage_name = api_json.get('stages', [{}])[0].get('stageName', 'prod')
    stage_log = sanitize_name(f"{api_json['name']}{stage_name}Stage")
    resources[stage_log] = {
        'Type': 'AWS::ApiGateway::Stage',
        'Properties': {
            'StageName': stage_name,
            'RestApiId': {'Ref': api_logical},
            'DeploymentId': {'Ref': deployment_log}
        }
    }
    
    template['Resources'] = resources
    
    template['Outputs'] = {
        'ApiEndpoint': {
            'Description': 'API Gateway Invoke URL',
            'Value': {'Fn::Sub': f"https://${{{api_logical}}}.execute-api.${{AWS::Region}}.amazonaws.com/{stage_name}"}
        }
    }
    return template

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Convert an API Gateway JSON export to a CloudFormation YAML template."
    )
    parser.add_argument('--input', required=True, help="Path to the input JSON file.")
    parser.add_argument('--output', required=True, help="Path for the output YAML file.")
    args = parser.parse_args()

    try:
        with open(args.input, 'r') as f:
            data = json.load(f)
        
        api_definition = data[0] if isinstance(data, list) and data else data
        
        cfn_template = convert_api_to_cfn(api_definition)
        
        with open(args.output, 'w') as f:
            yaml.dump(ordered_to_plain(cfn_template), f, sort_keys=False, default_flow_style=False, indent=2)
            
        print(f"Successfully converted '{args.input}' to '{args.output}'")

    except FileNotFoundError:
        print(f"Error: Input file not found at '{args.input}'")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{args.input}'. Please ensure it is a valid JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
