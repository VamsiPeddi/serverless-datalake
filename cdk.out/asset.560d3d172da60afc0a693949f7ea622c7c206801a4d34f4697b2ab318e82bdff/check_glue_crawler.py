#!/usr/bin/env python3.8
""" S3 List Lambda function

Lists files under an S3 prefix
"""

# imports added by Lambda layer
# pylint: disable=import-error
# import awswrangler as wr


# pylint: enable=import-error
from os import environ
import boto3
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)



glue_client = boto3.client("glue")
#glue_admin_role_name = environ['glue_admin_role_name']


crawler_name = 'person_crawler'


def lambda_handler(event, context):
    try:
        # get the crawler details
        response = glue_client.get_crawler(Name=crawler_name)
        # extract the crawler status
        crawler_status = response['Crawler']['State']
        logger.info(f' Status = {crawler_status}')
    except Exception as e:
        #event['status'] = "ERROR"
        raise(e)
        
    return crawler_status