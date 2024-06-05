from marshmallow import fields, validate, validates, ValidationError
from services.marshmallow import marshmallow as ma
from flask_smorest.fields import Upload
from application.models.news_model import NewsType


class LatestNewsSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    posted_by = fields.Integer(required=True)
    title = fields.String(required=True)
    news = fields.String(required=True)
    news_type = fields.String(
        required=False,
        validate=validate.OneOf(
            [NewsType.HEALTH_CARE.value, NewsType.OTHERS.value]
        ),
    )
    extra = fields.Dict(required=False)
    image = fields.Raw(type="file")
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    