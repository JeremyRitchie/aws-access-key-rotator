from aws_cdk import (
    Duration,
    Stack,
    aws_ses as ses,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_sns as sns,
)
from constructs import Construct

class AwsAccessKeyRotatorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        ses.EmailIdentity(
            self,
            "WorkIdentity",
            identity=ses.Identity.email("jeremy.ritchie@caylent.com"),
        )

        ses.EmailIdentity(
            self,
            "PersonalIdentity",
            identity=ses.Identity.email("jeremyritchie1996@hotmail.com"),
        )

        topic = sns.Topic(
            self,
            "FailureTopic",
            topic_name="access-key-rotation-notification"
        )

        sns.Subscription(
            self,
            "admin",
            topic=topic,
            protocol=sns.SubscriptionProtocol.EMAIL,
            endpoint="jeremyritchie1996@hotmail.com"
        )

        lambda_role = iam.Role(
            self,
            id="cdk-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name="cdk-lambda-role",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
                ),
                 iam.ManagedPolicy.from_aws_managed_policy_name(
                "AdministratorAccess"
                ),
            ],
        )
        # Defines an AWS Lambda resource
        function = lambda_.Function(
            self,
            "lambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            function_name="access-key-rotator",
            code=lambda_.Code.from_asset("./lambda"),
            handler="lambda_function.lambda_handler",
            role=lambda_role,
            environment={
                "sns_topic_arn": topic.topic_arn,
                "email_domain": "@caylent.com"},
            timeout=Duration.seconds(30)
        )

        function.add_permission(
            "SecretsManagerPolicy",
            principal=iam.ServicePrincipal("secretsmanager.amazonaws.com"),
        )
