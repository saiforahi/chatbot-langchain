import re
from marshmallow import ValidationError, fields, validate, validates, validates_schema
from application.models.userModel import User, MediumTypes, PreRegisteredUser
from services.marshmallow import marshmallow as ma


class RegistrationSchema(ma.Schema):
    id = fields.Integer(dump_only=True)

    first_name = fields.String(
        required=True,
        validate=[
            validate.Length(min=1, max=255, error="Invalid first name"),
            validate.Regexp(
                r"^[A-Za-z0-9\s]+$",
                error="Encouragement message must only contain letters, numbers, and spaces.",
            ),
        ],
    )
    last_name = fields.String(
        required=False,  # last_name optional
        allow_none=False,
    )
    emailOrPhone = fields.String(
        required=True,  # Make dataset_link optional
    )
    medium = fields.Enum(
        required=True, enum=MediumTypes, by_value=True  # Make dataset_link optional
    )
    password = fields.String(
        required=True,  # Make dataset_link optional
        validate=validate.Length(min=6, error="Password must be at least 8 characters"),
    )
    created_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True)

    @validates("emailOrPhone")
    def validate_emailOrPhone(self, value):
        if User.query.filter_by(emailOrPhone=value).first():
            raise ValidationError("An user already exists with this identity")
        elif "@" in value:
            if not validate.Email()(value):
                raise ValidationError("Invalid email address")
        else:
            # Check if the input looks like a phone number
            if not re.match(r"^\+\d{1,15}$", value):
                raise ValidationError("Invalid phone number format")


class LoginSchema(ma.Schema):
    medium = fields.Enum(required=True, enum=MediumTypes, by_value=True)
    emailOrPhone = fields.String(required=True)
    password = fields.String(
        required=True,
        validate=validate.Length(min=6, error="Password must be at least 8 characters"),
    )

    @validates("emailOrPhone")
    def validate_emailOrPhone(self, value):
        if not User.query.filter_by(emailOrPhone=value).first():
            raise ValidationError("No user found with this credential")
        elif "@" in value:
            if not validate.Email()(value):
                raise ValidationError("Invalid email address")
        else:
            # Check if the input looks like a phone number
            if not re.match(r"^\+\d{1,15}$", value):
                raise ValidationError("Invalid phone number format")


class ForgotPasswordRequestSchema(ma.Schema):
    emailOrPhone = fields.String(
        required=True, validate=validate.Length(min=1), data_key="emailOrPhone"
    )
    medium = fields.String(
        required=True, validate=validate.Length(min=1), data_key="medium"
    )
    reset_link = fields.String(
        required=True, validate=validate.Length(min=1), data_key="reset_link"
    )


class ForgotPasswordResetSchema(ma.Schema):
    emailOrPhone = fields.String(
        required=True, validate=validate.Length(min=5), data_key="emailOrPhone"
    )
    password = fields.String(
        required=True, validate=validate.Length(min=4), data_key="password"
    )


class UpdatePasswordSchema(ma.Schema):
    current_password = fields.String(required=True, validate=validate.Length(min=8))
    new_password = fields.String(required=True, validate=validate.Length(min=8))
    confirm_password = fields.String(required=True, validate=validate.Length(min=8))

    @validates_schema
    def validate_schema(self, data, **kwargs):
        if data["current_password"] == data["new_password"]:
            raise ValidationError(
                {
                    "new_password": [
                        "Current password and new password must be different"
                    ]
                }
            )


class RoleAssignSchema(ma.Schema):
    role_name = fields.String(
        required=True,
        # validate=validate.OneOf(
        #     [RoleTypes.ADMIN.value, RoleTypes.DR.value],
        # ),
    )


class PreRegSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    email = fields.String(required=True)
    from_location = fields.Function(lambda obj:obj.ip ,dump_only=True)
    created_at = fields.DateTime(required=False, dump_only=True, format='%Y-%m-%d %I:%M:%S %p')

    @validates("email")
    def validate_email(self, value):
        if "@" in value:
            if not validate.Email()(value):
                raise ValidationError("Invalid email address")

    @staticmethod
    def example():
        return [{
            "email":"abc@mail.com",
            "from_location":"Dhaka, Bangladesh"
        }]

class RegistrationLoginSchema(ma.Schema):
    emailOrPhone = fields.String(required=True,allow_none=False)
    first_name = fields.String(required=True,allow_none=False)
    last_name = fields.String(required=False)

    @validates("emailOrPhone")
    def validate_emailOrPhone(self, value):
        if "@" in value:
            if not validate.Email()(value):
                raise ValidationError("Invalid email address")
        else:
            # Check if the input looks like a phone number
            if not re.match(r"^\+\d{1,15}$", value):
                raise ValidationError("Invalid phone number format")


registrationSchema = RegistrationSchema()
loginSchema = LoginSchema()
