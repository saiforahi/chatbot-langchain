import hashlib


def encode_user_details(email, first_name):
    user_details = email + first_name
    encoded_user_details = hashlib.md5(user_details.encode())
    hax = (
        encoded_user_details.hexdigest()
    )  
    return hax

def encode_chatbot_details(bot_name, user_id):
    '''
    Generate a widget token for the chatbot
    param: bot_name: name of the chatbot
    param: user_id: id of the user
    return: str: widget token
    
    '''
    user_details = bot_name + user_id
    encoded_user_details = hashlib.md5(user_details.encode())
    hax = (
        encoded_user_details.hexdigest()
    )  
    return hax
