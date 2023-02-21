#!/usr/bin/env python3
import os

import aws_cdk as cdk

from aws_access_key_rotator.aws_access_key_rotator_stack import AwsAccessKeyRotatorStack


app = cdk.App()
AwsAccessKeyRotatorStack(app, "AwsAccessKeyRotatorStack",
    env=cdk.Environment(account='747340109238', region='ap-southeast-2'),
    )

app.synth()
