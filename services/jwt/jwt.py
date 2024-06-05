import secrets

from flask import jsonify
from flask_jwt_extended import JWTManager

from application.models.userModel import User

jwt = JWTManager()


# Register a callback function that takes whatever object is passed in as the
# identity when creating JWTs and converts it to a JSON serializable format.
def user_identity_lookup(user):
    return user


# Register a callback function that loads a user from your database whenever
# a protected route is accessed. This should return any python object on a
# successful lookup, or None if the lookup failed for any reason (for example
# if the user has been deleted from the database).
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.filter_by(emailOrPhone=identity).one_or_none()


def expired_token_callback(_jwt_header, jwt_data):
    return jsonify({
        'status': 401,
        'sub_status': 42,
        'msg': 'The token has expired'
    }), 401


jwt.user_lookup_loader(callback=user_lookup_callback)
jwt.user_identity_loader(callback=user_identity_lookup)
jwt.expired_token_loader(callback=expired_token_callback)


def generate_jwt_secret_key(length=64):
    return secrets.token_urlsafe(length)


if __name__ == "__main__":
    secret_key = generate_jwt_secret_key()
    print("Generated JWT Secret Key:", secret_key)
