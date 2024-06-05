from datetime import datetime, timedelta
import secrets
from application.models.userModel import PasswordResetToken
from database.service import db

def generate_reset_token(user_id):
    try:
        # Invalidate existing tokens for the user
        existing_tokens = PasswordResetToken.query.filter_by(user_id=user_id).all()
        for token in existing_tokens:
            db.session.delete(token)

        # Generate a new reset token
        expiration_time = datetime.utcnow() + timedelta(hours=1)
        token = generate_short_token()

        reset_token = PasswordResetToken(user_id=user_id, token=token, expiration_time=expiration_time)
        db.session.add(reset_token)
        db.session.commit()

        return token

    except Exception as e:
        db.session.rollback()
        raise e

def verify_reset_token(token):
    reset_token = PasswordResetToken.query.filter_by(token=token).first()

    if reset_token and reset_token.expiration_time > datetime.utcnow():
        # Token is valid
        return reset_token.user_id

    return None

def generate_short_token(length=6):
    # Generate a random token with the specified length using URL-safe characters
    return secrets.token_urlsafe(length)
