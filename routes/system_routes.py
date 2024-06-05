from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.site.utility_controller import UtilityController

system_routes_blueprint = Blueprint(
    "system", __name__, url_prefix="/api/system", description="System config detail endpoints"
)

@system_routes_blueprint.route('/config', methods=['GET'])
class SystemSettings(MethodView):
    @system_routes_blueprint.alt_response(status_code=200,example={"success":True,"message":"User updated","data":{}})
    def get(self):
        """System Settings Config API"""
        result = UtilityController().get_system_settings()
        return result

