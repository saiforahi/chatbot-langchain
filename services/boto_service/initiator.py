import boto3
from botocore.exceptions import NoCredentialsError
from config import AWS_DEFAULT_REGION,AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY


def boto3_session():
    try:
        session = boto3.session.Session(
            region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            # aws_session_token=AWS_SESSION_TOKEN
        )
        return session
    except NoCredentialsError as e:
        return str(e)
    except Exception as e:
        return None

bedrock_session  = boto3.Session( region_name=AWS_DEFAULT_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,)

def get_bedrock_client(runtime=False):
    return boto3_session().client('bedrock-runtime' if runtime else 'bedrock')

def get_logs_client():
    return boto3_session().client('logs')

def get_cloudwatch_client():
    return boto3_session().client('cloudwatch')


#  return boto3_session().client('bedrock-runtime' if runtime else 'chat').put_model_invocation_logging_configuration(
#         loggingConfig={
#             'cloudWatchConfig': {
#                 'logGroupName': log_group_name,
#                 'roleArn': 'arn:aws:iam::534678543881:role/admin_access'
#             },
#             'textDataDeliveryEnabled': True,
#             'imageDataDeliveryEnabled': True,
#             'embeddingDataDeliveryEnabled': True
#         }
#     )
