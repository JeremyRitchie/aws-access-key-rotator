from aws_cdk import (
    Stack,
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

        email_source = "jeremyritchie1996@hotmail.com"
        domain = "@caylent.com"

        # SES
        ses.EmailIdentity(
            self,
            "UserIdentity",
            identity=ses.Identity.email("jeremy.ritchie@caylent.com"),
        )

        ses.EmailIdentity(
            self,
            "EmailSource",
            identity=ses.Identity.email(email_source),
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
            endpoint=email_source
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
                "SecretsManagerReadWrite"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                "IAMFullAccess"
                )
            ],
            inline_policies={
                "SES": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["ses:SendEmail"],
                            effect=iam.Effect.ALLOW,
                            resources = ["*"]
                        )
                    ]
                ),
                "SNS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["sns:Publish"],
                            effect=iam.Effect.ALLOW,
                            resources = [topic.topic_arn]
                        )
                    ]
                )
            }
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
                "source_email": email_source,
                "email_domain": domain
            },
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