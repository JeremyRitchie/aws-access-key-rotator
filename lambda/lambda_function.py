import boto3
from botocore.exceptions import ClientError
import json
import logging
import sys, os

iam_client = boto3.client('iam')
secrets_client = boto3.client('secretsmanager')
ses_client = boto3.client('ses')
sns_client = boto3.client('sns')

# Init of the logging module
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] - %(message)s', force=True)

BODY = """
<p>Username: {}<br />Email: {}</p>
<p><strong><u>Your access key has been rotated. </u></strong><br />Please visit the following link to find your new access keys: {}</p>
<p>Access keys rotate every 90 days.<br />Please continue to use best practice and use IAM Roles where possible.<br /><br />See <a href="https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html" target="_blank" rel="noopener">here</a> for instructions on where to find the credential file on your local PC.</p>
<p>Thank you,<br />AWS Administrator</p>
"""

def create_key(username):
    try:
        access_key_metadata = iam_client.create_access_key(UserName=username)
        access_key = access_key_metadata['AccessKey']['AccessKeyId']
        secret_key = access_key_metadata['AccessKey']['SecretAccessKey']
        logging.info(access_key + " has been created.")
        return access_key, secret_key
    except ClientError as e:
        if e.response['Error']['Code'] == 'LimitExceededException':
            logging.error("Too many Access Key Tokens!!")
            sns_client.publish(TopicArn=os.environ['sns_topic_arn'], Message=f"Error rotating key: {username} - {str(e)}")
            raise e
        else:
            sns_client.publish(TopicArn=os.environ['sns_topic_arn'], Message=f"Error rotating key - creating new key: {username} - {str(e)}")
            raise e

def add_secret_version(secret_id, token, access_key, secret_key):
    secret = json.dumps({"access_key_id":access_key,"secret_access_key":secret_key})
    try:
        resp = secrets_client.put_secret_value(SecretId=secret_id,
            ClientRequestToken=token,
            SecretString=secret,
            VersionStages=['AWSPENDING',])
        logging.debug(resp)
    except secrets_client.exceptions.ResourceExistsException as e:
        sns_client.publish(TopicArn=os.environ['sns_topic_arn'], Message=f"Error rotating key - adding secert version - {str(e)}")
        raise e

def test_secret(secret_id, token, username):
    resp = secrets_client.get_secret_value(
        SecretId=secret_id,
        VersionId=token,
        VersionStage='AWSPENDING'
    )
    access_key_id = json.loads(resp['SecretString'])['access_key_id']
    secret_access_key = json.loads(resp['SecretString'])['secret_access_key']
    try:
        import time
        time.sleep(10) # Allow time for key to activate (2x factor of safety)
        boto3.client('iam', aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key).list_access_keys(UserName=username)
        logging.info("tests passed")
    except Exception as e:
        print("Error: " + str(e))
        sns_client.publish(TopicArn=os.environ['sns_topic_arn'], Message=f"Error rotating key - error testing key - {username} - {secret_id} - {str(e)}")
        raise e


def rotate_secret_version(secret_id, token):
    current_secret_versions = secrets_client.list_secret_version_ids(SecretId=secret_id)['Versions']
    for i in current_secret_versions:
        if i['VersionStages'][0] == 'AWSCURRENT':
            previous_secret_version = i['VersionId']
            secrets_client.update_secret_version_stage(
                SecretId=secret_id,
                VersionStage='AWSCURRENT',
                RemoveFromVersionId=previous_secret_version,
                MoveToVersionId=token
            )
            logging.info("Success in rotating")
            return
    logging.error("failure in rotating")
    sns_client.publish(TopicArn=os.environ['sns_topic_arn'], Message=f"Error rotating key - {secret_id}")
    raise ClientError

def revoke_old_access_keys(secret_id, token, username):
    secret_versions = secrets_client.list_secret_version_ids(SecretId=secret_id)

    for version in secret_versions['Versions']:
        if version['VersionStages'][0] == 'AWSPREVIOUS':
            current_version = version['VersionId']
            resp = secrets_client.get_secret_value(
                SecretId = secret_id,
                VersionId = current_version
            )
            access_key_id = json.loads(resp['SecretString'])['access_key_id']
            if len(access_key_id) > 16: # Check if key has any value to it. i.e this is not a fresh secret
                disable_key(access_key=access_key_id, username=username)
                delete_key(access_key=access_key_id, username=username)
                return

def disable_key(access_key, username):
    try:
        iam_client.update_access_key(UserName=username, AccessKeyId=access_key, Status="Inactive")
        logging.info(access_key + " has been disabled.")
    except Exception as e:
        logging.error(f"Error disabling key {access_key} - continuing")
        sns_client.publish(TopicArn=os.environ['sns_topic_arn'], Message=f"Error rotating key - error disabling key - {username} - {access_key} - {str(e)}")


def delete_key(access_key, username):
    try:
        iam_client.delete_access_key(UserName=username, AccessKeyId=access_key)
        logging.info(access_key + " has been deleted.")
    except Exception as e:
        logging.error(f"Error deleting key {access_key} - continuing")
        sns_client.publish(TopicArn=os.environ['sns_topic_arn'], Message=f"Error rotating key - error deleting key - {username} - {access_key} - {str(e)}")


def send_email(username, domain):
    try:
        dest_address = username + domain
        link = f'https://console.aws.amazon.com/secretsmanager/home'
        ses_client.send_email(Source=os.environ['source_email'],
            Destination={
                'ToAddresses': [
                    dest_address,
                ]
            },
            Message={
                'Subject': {
                    'Data': 'AWS Access Key Rotation',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': BODY.format(username, dest_address, link),
                        'Charset': 'UTF-8'
                    }
                }
            })
        logging.info("Email sucessfully sent!")
    except Exception as e:
        logging.error("Email not sent sucessfully.")
        logging.error(str(e))
        sns_client.publish(TopicArn=os.environ['sns_topic_arn'], Message=f"Error rotating key - error sending email - {username} - {str(e)}")

def check_current_secret(user, secret_id, secret_stage):
    secret = secrets_client.get_secret_value(SecretId=secret_id)
    secret_versions = secrets_client.list_secret_version_ids(SecretId=secret_id)['Versions']
    access_key_id = json.loads(secret['SecretString'])['access_key_id']
    user_keys = iam_client.list_access_keys(UserName=user)['AccessKeyMetadata']

    if secret_stage == 'createSecret':
        # Check number of secret versions
        if len(secret_versions) == 3: # This secret has been previous interrupted - check if iam matches secrets manager pending.
            for secret in secret_versions:
                if secret['VersionStages'][0] == 'AWSPENDING':
                    pending_access_key = secrets_client.get_secret_value(SecretId=secret_id, VersionStage='AWSPENDING')
                    for current_iam_key in user_keys:
                        if current_iam_key['AccessKeyId'] == json.loads(pending_access_key['SecretString'])['access_key_id']:
                            logging.info('Access key and pending secret match... skip createSecret stage')
                            return False
                    logging.error('Access key and pending secret DO NOT match...')
                    raise RuntimeError('Access key and pending secret DO NOT match...')

        elif len(secret_versions) <= 2: # Normal operation
            # Check number of access keys on user ~~~~~~~~~~~~
            if len(user_keys) == 1:
                logging.info("User has 1 access key currently")
            elif len(user_keys) == 2:
                # Delete key that is not in the secret
                logging.info("User has 2 access key currently - deleting any not in the current secret")
                for key in user_keys:
                    if key['AccessKeyId'] != access_key_id:
                        delete_key(access_key=key['AccessKeyId'], username=user)
    return True

def lambda_handler(event, context):
    domain = os.environ["email_domain"]

    secret_id = event['SecretId']
    secret_stage = event['Step']
    token = event['ClientRequestToken']
    username = secret_id.split('/')[-1].split('-')[0] # /access-key/jeremy.ritchie-823234

    logging.info(f"Stage: {secret_stage}, username: {username}, Token: {token}")


    if check_current_secret(username, secret_id, secret_stage):
        if secret_stage == 'createSecret':
            access_key, secret_key = create_key(username=username)
            add_secret_version(secret_id, token, access_key, secret_key)
        elif secret_stage == 'setSecret':
            pass
        elif secret_stage == 'testSecret':
            test_secret(secret_id, token, username)
        elif secret_stage == 'finishSecret':
            rotate_secret_version(secret_id, token)
            revoke_old_access_keys(secret_id, token, username)
            send_email(username, domain)
    return {
        'statusCode': 200,
        'body': 'success'
    }