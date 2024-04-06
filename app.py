#!/usr/bin/env python3

from aws_cdk import App

from serverless_datalake_stack.stack import ServerlessDataLakeStack


app = App()
ServerlessDataLakeStack(app, "ServerlessDataLakeStack")

app.synth()