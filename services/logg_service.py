import logging
from time import strftime
from services.boto_service.initiator import get_logs_client
import watchtower


def initiate_logger():
    # configure the logger handler to use CloudWatch
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    handler = watchtower.CloudWatchLogHandler(
        log_group="genai", stream_name=strftime("%Y-%m-%d"), create_log_group=True,
        boto3_client=get_logs_client()
    )
    logger.addHandler(handler)
    logger.info("GenAI Flask App Started")

    return logger