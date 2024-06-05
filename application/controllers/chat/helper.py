import csv
from datetime import datetime
import os
from application.models.topicModel import Topic
from application.models.customMessage import CustomMessage

MODEL_IDS = {
    "CLAUDE": 'anthropic.claude-v2:1',
    "TITAN": "amazon.titan-embed-text-v1",
    "OPENAI": "gpt-3.5-turbo-0613"
}


def write_history_csv_file(new_row=None):
    """
    :param file_content:
    """
    try:
        if not os.path.isdir("histories"):
            os.makedirs("histories")
            with open("./histories/seo.csv", "w") as file:
                writer = csv.writer(file)
                writer.writerows([['user','bot','input','output','timestamp'],new_row])
                file.close()
                return True
        else:
            with open("./histories/seo.csv", "a",newline='') as file:
                writer = csv.writer(file)
                writer.writerow(new_row)
                file.close()
                return True
    except Exception as e:
        print(str(e))
        pass

class PerDayMessageLimitExceededException(Exception):
    pass

    

def get_total_messages_sent_by_user_today(user_id):
    today_date = datetime.now().date()
   
    start_time = datetime.combine(today_date, datetime.min.time())
    end_time = datetime.combine(today_date, datetime.max.time())
   
    total_message = CustomMessage.query.join(Topic).filter(
        Topic.user_id == user_id,
        CustomMessage.created_at >= start_time,
        CustomMessage.created_at <= end_time,
        CustomMessage.type == 'human'
    ).count()
    return total_message
  


