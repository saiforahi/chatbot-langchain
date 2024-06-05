from flask import current_app
from flask_jwt_extended import current_user


def role_checker(role_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with current_app.app_context():
                # Your logic that requires the app context and decorator arguments
                print(f"Decorator arguments: {role_name}")
                return func(*args, **kwargs)
        return wrapper
    return decorator
