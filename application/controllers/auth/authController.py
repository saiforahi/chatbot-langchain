import datetime
import time

from dotenv import dotenv_values
from flask_jwt_extended import create_access_token, get_jwt_identity, current_user, create_refresh_token
from flask_mail import Message
from marshmallow import ValidationError
from application.controllers.utils import encode_user_details
from application.controllers.baseController import BaseController
from application.middlewares.role_checker import role_checker
from application.models.userModel import User, PasswordResetToken, PreRegisteredUser
from application.schemas.authSchemas import (
    RegistrationSchema,
    ForgotPasswordRequestSchema,
    ForgotPasswordResetSchema, PreRegSchema,
)
from flask import current_app, render_template, request

from application.schemas.user_schema import UserSchema, UserRoleSchema
from database.service import db
from services.celery.tasks import send_celery_email
from services.mail import mail
from application.models.roleModel import Role, RoleTypes
from application.models.roleModel import UserRole
from application.models.memberShipModels import MemberShipPlan, UserMembership
from services.passowrd_service.utils import generate_reset_token, verify_reset_token
from constants import DEFAULT_MEMBERSHIP_NAME
from flask_jwt_extended import current_user

current_user: User = current_user
launching_mail_template = "launching_mail.html"
pre_reg_mail_template = "pre_reg.html"
MAX_USER_PER_IP= dotenv_values(".env").get("MAX_USER_PER_IP", 5)

class AuthController(BaseController):
    def __init__(
            self,
    ) -> None:
        super().__init__()

    def assign_role(self, payload, user_id):
        try:
            if not current_user.is_admin():
                return self.error_response(message="You are not authorized to perform this action")
            user = User.query.get(user_id)
            if not user:
                return self.error_response(message="User not found")
            role = Role.query.filter_by(role_name=payload["role_name"]).first()
            if not role:
                return self.error_response(message="Role not found")
            # first check if the user already has the role
            user_role = UserRole.query.filter_by(user_id=user_id, role_id=role.id).first()
            if user_role:
                print("user_role", user_role)
                return self.error_response(message="User already has the role")
            user_role = UserRole(user=user, role=role)
            db.session.add(user_role)
            db.session.commit()
            return self.success_response(
                message="Role assigned successfully", data=UserRoleSchema().dump(user_role)
            )
        except Exception as e:
            return self.error_response(message="Role assignment failed", errors=str(e))

    def register(self, payload, is_admin=False, is_doctor=False):
        with current_app.app_context():
            try:
                if User.query.filter(User.created_using_ip==payload['created_using_ip']).count() >= int(MAX_USER_PER_IP):
                    raise Exception(f"Account creation limit({MAX_USER_PER_IP}) exceeded")
                schema = RegistrationSchema().load(payload)
                # passed validation
                user = User(**payload)
                user.set_password(password=payload["password"])
                db.session.add(user)

                user_roles = []
                # Set default role for the user, if the user is a doctor, then he/she will be assigned the role of a doctor, user and admin- all at once
                if is_admin:
                    user_roles = self.create_or_get_roles([RoleTypes.USER.value, RoleTypes.ADMIN.value])
                elif is_doctor:
                    user_roles = self.create_or_get_roles(
                        [RoleTypes.USER.value, RoleTypes.ADMIN.value, RoleTypes.DR.value])
                else:
                    user_roles = self.create_or_get_roles([RoleTypes.USER.value])

                for role in user_roles:
                    user_role = UserRole(user=user, role=role)
                    db.session.add(user_role)

                self.add_to_default_membership(user.id, user.emailOrPhone, user.first_name)
                return self.success_response(
                    message="Registration succeed",
                    data=RegistrationSchema(exclude=["password"]).dump(user),
                )
            except ValidationError as e:
                db.session.rollback()
                return self.error_response(
                    message="Registration failed", errors=e.messages, status_code=400
                )
            except Exception as e:
                db.session.rollback()
                return self.error_response(
                    message=str(e), errors=str(e), status_code=500
                )
            finally:
                db.session.commit()
                db.session.close()

    def pre_registration(self, payload):
        try:
            if User.query.filter_by(emailOrPhone=payload["email"]).first() or PreRegisteredUser.query.filter_by(
                    email=payload["email"]).first():
                raise ValidationError("You are already pre-registered")
            pre_reg_user = PreRegisteredUser(**payload, created_at=datetime.datetime.now())
            db.session.add(pre_reg_user)
            db.session.flush()
            mail_send_task = send_celery_email.delay(to_emails=[payload['email']], template=pre_reg_mail_template,
                                                     subject="Your DocAdvisor Pre-Registration: Confirmed!")
            return self.success_response(message="Pre Registration succeeded",
                                         data=PreRegSchema(many=False).dump(pre_reg_user), status_code=200)
        except Exception as e:
            db.session.rollback()
            return self.error_response(message=str(e), errors=[str(e)], status_code=400)
        finally:
            db.session.commit()
            db.session.close()

    def registration_login(self, payload):
        response = {
            "idToken": '',
            "refreshToken": '',
            "user": {},
            "is_new_user": False
        }
        try:
            user = User.query.filter_by(emailOrPhone=payload['emailOrPhone']).first()
            if user is None:
                if User.query.filter(User.created_using_ip==payload['created_using_ip']).count() >= int(MAX_USER_PER_IP):
                    raise Exception(f"Account creation limit({MAX_USER_PER_IP}) exceeded")

                user = User(**payload, last_login_ip=payload['created_using_ip'])
                user.set_password(password=str(time.time() * 1000))
                db.session.add(user)

                user_roles = self.create_or_get_roles([RoleTypes.USER.value])
                for role in user_roles:
                    user_role = UserRole(user=user, role=role)
                    db.session.add(user_role)

                self.add_to_default_membership(user.id, user.emailOrPhone, user.first_name)
                response['is_new_user'] = True
            else:
                user.first_name = payload['first_name']
                user.last_name = payload['last_name']
                user.last_login_ip = payload['created_using_ip']

            db.session.flush()
            response["idToken"] = create_access_token(identity=payload['emailOrPhone'], fresh=True)
            response["refreshToken"] = create_refresh_token(identity=payload['emailOrPhone'])
            response["user"] = UserSchema(many=False).dump(user)
            return self.success_response(message="Simple Registration Login succeeded", data=response, status_code=200)
        except Exception as e:
            db.session.rollback()
            print(str(e))
            return self.error_response(message=str(e), errors=[str(e)], status_code=400)
        finally:
            db.session.commit()
            db.session.close()

    def launching_send_email(self):
        pre_registered_users = PreRegisteredUser.query.all()
        if pre_registered_users:
            for users in pre_registered_users:
                mail_send_task = send_celery_email.delay(to_emails=[users.email], template=launching_mail_template,
                                                         subject="DocAdvisor App Now Live – Check It Out!")
        return self.success_response(message="Launching mail send successfully",
                                     data=PreRegSchema(many=False).dump(pre_registered_users), status_code=200)

    def create_or_get_roles(self, role_name_list):
        try:
            roles = []
            for role_name in role_name_list:
                role = Role.query.filter_by(role_name=role_name).first()
                if role:
                    roles.append(role)
                else:
                    role = Role(role_name=role_name)
                    db.session.add(role)
                    db.session.flush()
                    roles.append(role)
            return roles
        except Exception as e:
            db.session.rollback()
            raise Exception(str(e))
        finally:
            db.session.commit()
            db.session.close()

    @role_checker(role_name="admin")
    def login(self, payload):
        try:
            username = payload["emailOrPhone"]
            password = payload["password"]
            user = User.query.filter_by(emailOrPhone=username).first()
            if user and user.check_password(password):
                user.last_login_ip=payload['last_login_ip']
                db.session.flush()
                data = {
                    "idToken": create_access_token(identity=username, fresh=True),
                    "refreshToken": create_refresh_token(identity=username),
                    "user": UserSchema(many=False).dump(user),
                }
                return self.success_response(message="Login succeed", data=data)
            else:
                raise Exception("Invalid credentials")
        except Exception as e:
            current_app.logger.info(str(e))
            return self.error_response(
                message=str(e), status_code=500
            )
        finally:
            db.session.commit()
            db.session.close()

    def refresh(self):
        try:
            identity = get_jwt_identity()
            print('id', identity)
            access_token = create_access_token(identity=identity, fresh=False)
            return self.success_response(message="Token refreshed", data={'idToken': access_token})
        except Exception as e:
            print(str(e))
            current_app.logger.info(str(e))
            return self.success_response(message="Token refresh failed")

    def user_identity(self):
        try:
            current_user = get_jwt_identity()
            return self.success_response(message="Logged in as", data=current_user)
        except Exception as e:
            return self.error_response(
                message="Login failed", errors=str(e), status_code=500
            )

    def forgot_password(self, payload):
        try:
            # Validate the request payload
            schema = ForgotPasswordRequestSchema().load(payload)

            # Check if the user with the given email/phone exists
            user = User.query.filter_by(emailOrPhone=schema["emailOrPhone"]).first()
            print(user)
            if user:
                # Generate a reset password token
                reset_token = generate_reset_token(user.id)

                # Concatenate the reset token and path to form the reset link
                reset_link = f"{schema.get('reset_link')}?token={reset_token}&email_or_phone={user.emailOrPhone}"

                subject = "Reset Your Password"
                template = f"Visit this link to reset your password {reset_link}"
                self.send_forget_pass_mail(
                    to=[user.emailOrPhone],
                    subject=subject,
                    template=template,
                    reset_link=reset_link,
                )

                return self.success_response(
                    message="Password reset link sent successfully", data=None
                )
            else:
                raise Exception("User not found")

        except ValidationError as e:
            return self.error_response(
                message="Validation error", errors=e.messages, status_code=400
            )
        except Exception as e:
            return self.error_response(
                message="Password reset failed", errors=str(e), status_code=500
            )

    def reset_forgotten_password(self, payload, token):
        try:
            verified_user_id = verify_reset_token(token)
            if verified_user_id:
                # Validate the request payload
                schema = ForgotPasswordResetSchema().load(payload)

                # Check if the user with the given email/phone exists
                user = User.query.filter_by(id=verified_user_id).first()
                if user:
                    # Update the user's password
                    user.set_password(schema.get("password"))
                    # makes is_used field to True in PasswordResetToken table
                    reset_token = PasswordResetToken.query.filter_by(
                        token=token
                    ).first()
                    reset_token.is_used = True
                    db.session.commit()

                    return self.success_response(
                        message="Password reset succeed", data=None
                    )
                else:
                    raise Exception("User not found")
            else:
                raise Exception("Invalid token")
        except ValidationError as e:
            return self.error_response(
                message="Validation error", errors=e.messages, status_code=400
            )
        except Exception as e:
            return self.error_response(
                message="Password reset failed", errors=str(e), status_code=500
            )

    def update_password(self, payload):
        try:
            emailOrPhone = get_jwt_identity()
            print("emailOrPhone", emailOrPhone)
            user = User.query.filter_by(emailOrPhone=emailOrPhone).first()
            print("user", user)

            if not user or not user.check_password(payload["current_password"]):
                raise ValidationError(
                    {"current_password": ["Invalid current password"]}
                )

            if payload["new_password"] != payload["confirm_password"]:
                raise ValidationError(
                    {"confirm_password": ["New password is not confirmed"]}
                )

            # Update the password
            user.set_password(payload["new_password"])
            db.session.commit()

            return self.success_response(message="Password updated successfully")

        except ValidationError as e:
            return self.error_response(
                message="Validation error", errors=e.messages, status_code=400
            )
        except Exception as e:
            return self.error_response(
                message="Password update failed", errors=str(e), status_code=500
            )

    def send_forget_pass_mail(self, to, subject, template, **kwargs):
        print("to", to)
        print("subject", subject)
        print("template", template)
        print("kwargs", kwargs)

        try:
            msg = Message(
                subject=subject,
                sender=current_app.config["MAIL_USERNAME"],
                recipients=to,
            )
            # msg.body = render_template("template.txt", **kwargs)
            msg.html = render_template("forget_pass.html", **kwargs)
            print(msg)
            mail.send(msg)
        except Exception as e:
            print("mail send err : ", str(e))
        # with current_app.app_context():
        #     mail.send(msg)

    def add_to_default_membership(self, user_id, emailOrPhone, first_name):
        membership_plan = MemberShipPlan.query.filter_by(
            name=DEFAULT_MEMBERSHIP_NAME
        ).first()
        if membership_plan:
            # membership_token = encode_user_details(
            #     email=emailOrPhone, first_name=first_name
            # )
            user_membership = UserMembership(
                user_id=user_id,
                membership_plan_id=membership_plan.id,
                # membership_token=membership_token,
                is_active=True,
            )
            db.session.add(user_membership)

        else:
            raise Exception("Default membership plan not found")
