#!/usr/bin/env python3
"""
Convert API Gateway export JSON into a CloudFormation YAML template,
with full CORS support and correct IAM role for Lambda integrations.
When an Integration requires credentials, uses arn:aws:iam::${AWS::AccountId}:role/LabRole.
Includes propagation of method.request querystring parameters.
"""
import json
import yaml
import re
import argparse
from collections import OrderedDict
from datetime import datetime, timezone

# Helper to sanitize names for CloudFormation logical IDs
def sanitize_name(name):
    parts = re.split(r'[^0-9a-zA-Z]+', name)
    return ''.join([part.capitalize() for part in parts if part])

# Convert OrderedDict to plain dicts for YAML serialization
def ordered_to_plain(obj):
    if isinstance(obj, OrderedDict): obj = dict(obj)
    if isinstance(obj, dict): return {k: ordered_to_plain(v) for k, v in obj.items()}
    if isinstance(obj, list): return [ordered_to_plain(v) for v in obj]
    return obj

# Main conversion
def convert_api_to_cfn(api_json):
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    template = OrderedDict()
    template['AWSTemplateFormatVersion'] = '2010-09-09'
    template['Description'] = f"CloudFormation template for API Gateway API: {api_json.get('name')}"
    template['Parameters'] = {
        'EnvPrefix': {
            'Type': 'String',
            'Description': 'Environment prefix',
            'MinLength': 1
        }
    }
    resources = OrderedDict()
    api_logical = sanitize_name(api_json['name'] + 'RestApi')
    resources[api_logical] = {
        'Type': 'AWS::ApiGateway::RestApi',
        'Properties': {
            'Name': {'Fn::Sub': '${EnvPrefix}' + api_json['name']},
            'EndpointConfiguration': {'Types': ['REGIONAL']}
        }
    }
    # Build resource ID map
    id_map = {}
    for res in api_json['resources']:
        id_map[res['id']] = None if res['path']=='/' else sanitize_name(api_json['name'] + res['path'].replace('/', '_') + 'Resource')
    # Create Resource objects
    for res in api_json['resources']:
        if res['path']=='/': continue
        logical = id_map[res['id']]
        parent = res.get('parentId')
        parent_ref = {'Fn::GetAtt': [api_logical,'RootResourceId']} if id_map.get(parent) is None else {'Ref': id_map[parent]}
        resources[logical] = {
            'Type': 'AWS::ApiGateway::Resource',
            'Properties': {
                'RestApiId': {'Ref': api_logical},
                'ParentId': parent_ref,
                'PathPart': res['pathPart']
            }
        }
    method_ids=[]
    # Methods and CORS
    for res in api_json['resources']:
        res_ref = {'Fn::GetAtt':[api_logical,'RootResourceId']} if res['path']=='/' else {'Ref':id_map[res['id']]}
        for http_method, method_def in res.get('resourceMethods',{}).items():
            method_log = sanitize_name(api_json['name'] + res['path'].replace('/','_') + http_method + 'Method')
            method_ids.append(method_log)
            # Prepare RequestParameters for querystring
            req_params = {}
            for p,v in method_def.get('requestParameters',{}).items():
                req_params[p] = True
            props = {
                'RestApiId':{'Ref':api_logical},
                'ResourceId':res_ref,
                'HttpMethod':http_method,
                'AuthorizationType':method_def.get('authorizationType','NONE'),
                'ApiKeyRequired':method_def.get('apiKeyRequired',False),
                'RequestParameters': req_params,
                'Integration':{},
                'MethodResponses':[{
                    'StatusCode':'200',
                    'ResponseModels':{'application/json':'Empty'},
                    'ResponseParameters':{'method.response.header.Access-Control-Allow-Origin':False}
                }]
            }
            integ = method_def.get('methodIntegration',{})
            if integ:
                iobj={'Type':integ['type']}
                raw_uri=integ.get('uri')
                if integ['type'] in ['AWS','AWS_PROXY'] and raw_uri:
                    m=re.search(r'function:([^/]+)/invocations',raw_uri)
                    if m:
                        fn=m.group(1)
                        iobj['Uri']={'Fn::Sub':(
                            f"arn:aws:apigateway:${{AWS::Region}}:lambda:path/2015-03-31/functions/arn:aws:lambda:${{AWS::Region}}:${{AWS::AccountId}}:function:${{EnvPrefix}}-{fn}/invocations"
                        )}
                    else:
                        iobj['Uri']=raw_uri
                    iobj['IntegrationHttpMethod']=integ.get('httpMethod','POST')
                    iobj['Credentials']={'Fn::Sub':'arn:aws:iam::${AWS::AccountId}:role/LabRole'}
                if integ.get('requestParameters'):
                    iobj['RequestParameters']=integ['requestParameters']
                if integ.get('requestTemplates'):
                    iobj['RequestTemplates']=integ['requestTemplates']
                for k in ['passthroughBehavior','contentHandling','timeoutInMillis','cacheNamespace','cacheKeyParameters']:
                    if k in integ:
                        iobj[k[0].upper()+k[1:]]=integ[k]
                iobj['IntegrationResponses']=[{
                    'StatusCode':'200',
                    'ResponseParameters':{'method.response.header.Access-Control-Allow-Origin':"'*'"}
                }]
                props['Integration']=iobj
            resources[method_log]={'Type':'AWS::ApiGateway::Method','Properties':props}
            # CORS OPTIONS
            opt_log=sanitize_name(api_json['name']+res['path'].replace('/','_')+'OptionsMethod')
            cors={
                'StatusCode':'200',
                'ResponseParameters':{
                    'method.response.header.Access-Control-Allow-Headers':"'Content-Type,Authorization,X-Amz-Date,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods':f"'{','.join(method_def.get('resourceMethods',{}).keys())},OPTIONS'",
                    'method.response.header.Access-Control-Allow-Origin':"'*'"
                }
            }
            resources[opt_log]={'Type':'AWS::ApiGateway::Method','Properties':{
                'RestApiId':{'Ref':api_logical},
                'ResourceId':res_ref,
                'HttpMethod':'OPTIONS',
                'AuthorizationType':'NONE',
                'Integration':{'Type':'MOCK','RequestTemplates':{'application/json':'{"statusCode":200}'},'IntegrationResponses':[cors]},
                'MethodResponses':[{'StatusCode':'200','ResponseModels':{'application/json':'Empty'},'ResponseParameters':{p:False for p in cors['ResponseParameters']}}]
            }}
            method_ids.append(opt_log)
    # Deployment
    dep_log=sanitize_name(api_json['name']+'Deployment')
    resources[dep_log]={'Type':'AWS::ApiGateway::Deployment','DependsOn':method_ids,'Properties':{
        'RestApiId':{'Ref':api_logical},
        'StageName':{'Fn::Sub':f'${{EnvPrefix}}-{timestamp}'}
    }}
    template['Resources']=resources
    template['Outputs']={'ApiEndpoint':{'Description':'Invoke URL','Value':{'Fn::Sub':f"https://${{{api_logical}}}.execute-api.${{AWS::Region}}/{timestamp}"}}}
    return template

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--output',required=True)
    args=p.parse_args()
    data=json.load(open(args.input))
    api=data[0] if isinstance(data,list) and data else data
    tpl=convert_api_to_cfn(api)
    with open(args.output,'w') as f:
        yaml.safe_dump(ordered_to_plain(tpl),f,sort_keys=False)
