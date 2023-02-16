from aws_cdk import (
    Duration,
    SecretValue,
    Stack,
    aws_ses as ses,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_sns as sns,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

class AwsAccessKeyRotatorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SES
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

        # SNS
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

        # Lambda
        lambda_role = iam.Role(
            self,
            id="lambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name="access-key-rotator-role",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
                ),
                 iam.ManagedPolicy.from_aws_managed_policy_name(
                "AdministratorAccess"
                ),
            ],
        )

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

        users = ['jeremy.ritchie']
        # Secrets
        for user in users:
            secret = secretsmanager.Secret(
                self,
                f"{user.replace('.','')}Secret",
                secret_name=f"/access-key/{user}",
                secret_object_value={
                    "access_key_id": SecretValue.unsafe_plain_text("foo"),
                    "secret_access_key": SecretValue.unsafe_plain_text("bar"),
                }
            )
            secret.add_rotation_schedule(
                 f"{user.replace('.','')}Rotation",
                automatically_after=Duration.days(90),
                rotation_lambda=function
            )