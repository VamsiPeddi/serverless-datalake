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
import botocore
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)



glue = boto3.client("glue")

glue_admin_role_name = environ['glue_admin_role_name']

# -------------------------------------------------
# Create new glue crawler
# -------------------------------------------------
def create_crawler(glue, glue_db_name, glue_admin_role_name, crawler_name, source_file_path):
    try:
        # call the get crawler, if response fails then crawler is not defined
        response = glue.create_crawler(
            Name=crawler_name,
            DatabaseName=glue_db_name,
            Role=glue_admin_role_name,
            Description='Crawler to create catalog table ',
            Targets={
                'S3Targets': [
                    {
                        'Path': source_file_path,
                        'Exclusions': [ '*/.raw/*']
                    },
                ]
            },
            SchemaChangePolicy={
                'UpdateBehavior': 'UPDATE_IN_DATABASE',
                'DeleteBehavior': 'DELETE_FROM_DATABASE'
            },
            Configuration='{ "Version": 1.0, "CrawlerOutput": { "Partitions": { "AddOrUpdateBehavior": "InheritFromTable" } } }',
            Tags={'app-category': 'daas'}
        )
        return response
    except Exception as e:
        raise Exception(f'Unable to create crawler! {e}')

# -------------------------------------------------
# Create the new glue crawler
# -------------------------------------------------
def start_crawler(glue_client, crawler_name):
    try:
        response = glue_client.start_crawler(
            Name=crawler_name
        )
        return response
    except Exception as e:
        raise Exception(f'Unable to start crawler! {e}')


def is_crawler_not_exist(crawler_name):
    try:
        response = glue.get_crawler(Name=crawler_name)
        print(f"Crawler {crawler_name} exists.")
        return False
    except botocore.exceptions.ClientError as e:
        print(f"Crawler {crawler_name} does not exist.")
        return True


def lambda_handler(event, context):
    try:
        glue_db_name = "legislators"

        crawler_name="person_crawler"
        try : 
                response = glue.create_database(
                    DatabaseInput={
                        'Name': glue_db_name
                    }
                )
                logger.info(f"Glue database '{glue_db_name}' created successfully.")
        except Exception as e:
                logger.info(f"Glue database '{glue_db_name}' already exists .")

        source_file_path = "s3://balaaws-s3-ingest-321/input/"

        if is_crawler_not_exist(crawler_name):
            create_crawler(glue,glue_db_name,glue_admin_role_name,crawler_name,source_file_path)
            start_crawler(glue, crawler_name)
        

    except Exception as e:
        raise(e)

    event['status'] = "RUNNING"

    return event