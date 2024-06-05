from flask.views import MethodView
from flask_smorest import Blueprint, abort
from application.controllers.bot.llm_controller import LlmController
from application.schemas.llm_schema import LlmSchema, LlmUpdateSchema

# role_blueprint = Blueprint('role', 'role', url_prefix='/api', description='Role Operations')
llm_blueprint = Blueprint(
    "llm", __name__, description="Operations on llm", url_prefix="/api"
)



@llm_blueprint.route("/llms")
class LlmList(MethodView):
    @llm_blueprint.response(200, LlmSchema(many=True))
    def get(self):
        """Get all llms"""
        return LlmController().get_llms()

    @llm_blueprint.arguments(LlmSchema)
    @llm_blueprint.response(201, LlmSchema)
    def post(self, payload):
        """Create a new llm"""
        return LlmController().create_llm(payload)
    
@llm_blueprint.route("/llms/<int:llm_id>")
class Llm(MethodView):
    @llm_blueprint.response(200, LlmSchema)
    def get(self, llm_id):
        """Get llm by id"""
        return LlmController().get_llm(llm_id)

    @llm_blueprint.arguments(LlmUpdateSchema)
    @llm_blueprint.response(200, LlmSchema)
    def patch(self, payload, llm_id):
        """Update llm by id"""
        return LlmController().update_llm(llm_id, payload)

    @llm_blueprint.response(204)
    def delete(self, llm_id):
        """Delete llm by id"""
        return LlmController().delete_llm(llm_id)