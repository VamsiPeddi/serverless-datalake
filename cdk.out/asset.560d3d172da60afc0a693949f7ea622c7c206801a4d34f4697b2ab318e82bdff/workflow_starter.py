#!/usr/bin/env python3.8
""" Incoming Semarchy Workflow Starter

Entry point into the Incoming Semarchy process.
Subscribes to an SQS Queue. Messages in the queue pass an S3 partition.
Starts the Step Function State Machine for the S3 partition
"""
import json
from os import environ
import boto3
import urllib
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)

STATE_MACHINE_ARN = environ["STATE_MACHINE_ARN"]
SFN_CLIENT = boto3.client("stepfunctions")


def invoke_controller_stepfunction(source_bucket, source_key, region):
    try:
        stpfn_client = boto3.client('stepfunctions')
        glue_db_name = "legislators"
        params = {
            'database_name': glue_db_name,
            'region': region,
            'source_bucket': source_bucket,
            'source_key': source_key,
            'region': region
        }
        logger.info("starting workfow: %s", STATE_MACHINE_ARN)
        response = SFN_CLIENT.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(params),
        )
        logger.debug("response: %s", response)
    except Exception as e:
        raise Exception(f'Failed while invoking step function {STATE_MACHINE_ARN}  {e}')
    
    
def lambda_handler(event, context):
    json_event = json.dumps(event)
    logger.info(f'{json_event}')
    resp=""
    if len(event['Records']) >= 1:
        try:
            for record in json.loads(event['Records'][0]['body'])['Records']:
                source_bucket = record['s3']['bucket']['name']
                source_key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
                region = record['awsRegion']
                logger.info(f'{source_bucket}')
                logger.info(f'{source_key}')
                logger.info(f'{region}')
              
                invoke_controller_stepfunction(source_bucket,source_key,region)
        except Exception as e:
            logger.info(f'Error Occured {e}')
            return {
                'body': json.loads(json.dumps(e, default=str)),
                'statusCode': 400
            }