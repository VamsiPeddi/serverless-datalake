from aws_cdk import (
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    aws_stepfunctions as stepfunctions,
    aws_stepfunctions_tasks as tasks,
    App,
    Aws,
    Stack,
    CfnParameter,
    aws_stepfunctions as _aws_stepfunctions,
    aws_stepfunctions_tasks as _aws_stepfunctions_tasks,
    aws_s3_notifications as s3n,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_sqs as sqs,
    Duration,
    aws_lambda_event_sources as lambda_events
)
from constructs import Construct


class ServerlessDataLakeStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #lambda_dir = kwargs["lambda_dir"]
        # ==============================
        # ======= CFN PARAMETERS =======
        # ==============================
        project_name_param = "vamsi-datalake-test"
        #db_name = "mlflowdb2"
        #port = 3306
        #username = "master"
        bucket_name = f"{project_name_param}-artifacts-{Aws.ACCOUNT_ID}"
        # container_repo_name = "mlflow-containers"
        # cluster_name = "mlflow"
        # service_name = "mlflow"

        # ==================================================
        # ================= IAM ROLE =======================
        # ==================================================
        role = iam.Role(
            scope=self,
            id="TASKROLE",
            assumed_by=iam.ServicePrincipal(service="ecs-tasks.amazonaws.com"),
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
        )

        # ==================================================
        # ================= S3 BUCKET ======================
        # ==================================================
        artifact_bucket = s3.Bucket(
            scope=self,
            id="ARTIFACTBUCKET",
            bucket_name=bucket_name,
            public_read_access=False,
        )

        # ==================================================
        # ================ SQS Queues ======================
        # ==================================================
        dlq = sqs.Queue(
            self,
            id="dead_letter_queue_id",
            retention_period=Duration.days(7)
        )
        
        dead_letter_queue = sqs.DeadLetterQueue(
            max_receive_count=1,
            queue=dlq
        )

        upload_queue = sqs.Queue(
            self,
            id="sample_queue_id",
            dead_letter_queue=dead_letter_queue,
            visibility_timeout = Duration.seconds(10 * 6)
        )

        sqs_subscription = sns_subs.SqsSubscription(
            upload_queue,
            raw_message_delivery=True
        )

        upload_event_topic = sns.Topic(
            self,
            id="sample_sns_topic_id"
        )

        # This binds the SNS Topic to the SQS Queue
        upload_event_topic.add_subscription(sqs_subscription)

        # Note: If you don't specify a filter all uploads will trigger an event.
        # Also, modifying the event type will handle other object operations
        # This binds the S3 bucket to the SNS Topic
        artifact_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED_PUT,
            s3n.SnsDestination(upload_event_topic),
            s3.NotificationKeyFilter(prefix="uploads", suffix=".csv")
        )


        # Lambda Handlers Definitions
        workflow_starter = _lambda.Function(self, 'startLambda',
                                         handler='workflow_starter.lambda_handler',
                                         runtime=_lambda.Runtime.PYTHON_3_9,
                                         code=_lambda.Code.from_asset('lambda'))
        
        # This binds the lambda to the SQS Queue
        invoke_event_source = lambda_events.SqsEventSource(upload_queue)
        workflow_starter.add_event_source(invoke_event_source)

        run_glue_crawler = _lambda.Function(self, 'runLambda',
                                         handler='run_glue_crawler.lambda_handler',
                                         runtime=_lambda.Runtime.PYTHON_3_9,
                                         code=_lambda.Code.from_asset('lambda'))
        
        check_glue_crawler = _lambda.Function(self, 'checkLambda',
                                         handler='check_glue_crawler.lambda_handler',
                                         runtime=_lambda.Runtime.PYTHON_3_9,
                                         code=_lambda.Code.from_asset('lambda'))

        # Step functions Definition

        start_job = _aws_stepfunctions_tasks.LambdaInvoke(
            self, "Start Job",
            lambda_function=workflow_starter,
            output_path="$.Payload",
        )

        wait_job = _aws_stepfunctions.Wait(
            self, "Wait 30 Seconds",
            time=_aws_stepfunctions.WaitTime.duration(
                Duration.seconds(30))
        )

        run_job = _aws_stepfunctions_tasks.LambdaInvoke(
            self, "Run Crawler",
            lambda_function=run_glue_crawler,
            output_path="$.Payload",
        )

        check_job = _aws_stepfunctions_tasks.LambdaInvoke(
            self, "Check Crawler",
            lambda_function=check_glue_crawler,
            output_path="$.Payload",
        )
        fail_job = _aws_stepfunctions.Fail(
            self, "Fail",
            cause='AWS Batch Job Failed',
            error='DescribeJob returned FAILED'
        )

        succeed_job = _aws_stepfunctions.Succeed(
            self, "Succeeded",
            comment='AWS Batch Job succeeded'
        )


        # Create Chain
        chain = start_job.next(wait_job)\
            .next(run_job)\
            .next(check_job)

        # Create state machine
        sm = _aws_stepfunctions.StateMachine(
            self, "StateMachine",
            definition_body=_aws_stepfunctions.DefinitionBody.from_chainable(chain),
            timeout=Duration.minutes(5),
        )




app = App()
ServerlessDataLakeStack(app, "ServerlessDataLakeStack")
app.synth()
