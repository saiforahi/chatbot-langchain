from flask.views import MethodView
from flask_smorest import Blueprint, abort
from application.controllers.user.pre_registered_user_controller import PreRegisteredUserController
from application.schemas.authSchemas import PreRegSchema

pre_registration_bp = Blueprint('pre_registration', 'pre_registration', url_prefix='/api/pre-reg', description='Pre Registration Operations')


@pre_registration_bp.route('/')
class PreRegisteredUser(MethodView):
    """Role Operations"""

    @pre_registration_bp.alt_response(status_code=200, schema=PreRegSchema(many=True),example=PreRegSchema.example())
    def get(self):
        """Get all pre registered users"""
        try:
            users = PreRegisteredUserController().get_list()
            return users
        except Exception as e:
            abort(500, message=str(e))
