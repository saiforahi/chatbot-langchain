from dotenv import dotenv_values

APP_ENV = dotenv_values(".env").get("APP_ENV")
MYSQL_ENVS=['dev','stage','qa']
MYSQL_CONFIGS = {
    'dev_local': {
        "mysql_db": "genai_flask_db_dev",
        "mysql_user": "root",
        "mysql_pwd": "Shadhinai2023",
        "mysql_host": "database-1.c66copzd5ocy.us-east-1.rds.amazonaws.com",
        "mysql_port": "3306"
    },
    "live": {
        "mysql_db": dotenv_values(".env").get("DB_NAME"),
        "mysql_user": dotenv_values(".env").get("DB_USER"),
        "mysql_pwd": dotenv_values(".env").get("DB_PASSWORD"),
        "mysql_host": dotenv_values(".env").get("DB_HOST"),
        "mysql_port": dotenv_values(".env").get("DB_PORT")
    },
    "fuad_dev": {
        "mysql_db": dotenv_values(".env").get("fuad_DB_NAME"),
        "mysql_user": dotenv_values(".env").get("fuad_DB_USER"),
        "mysql_pwd": dotenv_values(".env").get("fuad_DB_PASSWORD"),
        "mysql_host": dotenv_values(".env").get("fuad_DB_HOST"),
        "mysql_port": dotenv_values(".env").get("fuad_DB_PORT")
    },
    'dev_arif': {
        "mysql_db": "genai_flask_db",
        "mysql_user": "root",
        "mysql_pwd": "toor",
        "mysql_host": "localhost",
        "mysql_port": "3306"
    },
}


def get_db_config(env) -> dict:
    if env in MYSQL_ENVS:
        return MYSQL_CONFIGS.get('live')
    elif env == 'fuad_dev':
        print('fuad_dev')
        return MYSQL_CONFIGS.get('fuad_dev')
    return MYSQL_CONFIGS.get('dev_local')


# mysql+pymysql://<username>:<password>@<host>:<port>/<database_name>
connection_config:dict=get_db_config(APP_ENV)
connection_str = f'mysql+pymysql://{connection_config.get("mysql_user")}:{connection_config.get("mysql_pwd")}@{connection_config.get("mysql_host")}:{connection_config.get("mysql_port")}/{connection_config.get("mysql_db")}'
