from flask import request, jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required, current_user
from flask_smorest import Blueprint

from application.controllers.user.userController import UserController
from application.helper import get_location_from_google_maps
from application.schemas.user_schema import UserSchema, UserListSchema

user_blueprint = Blueprint('user', __name__, url_prefix='/api/user', description="User management endpoints")


@user_blueprint.route('/update', methods=['POST'])
class UpdateUser(MethodView):
    @user_blueprint.arguments(UserSchema)
    @user_blueprint.alt_response(status_code=200,example={"success":True,"message":"User updated","data":{}})
    @jwt_required()
    def post(self,*args,**kwargs):
        result = UserController().update_user(payload=dict(args[0]),user_id=current_user.id)
        return result

@user_blueprint.route('/detail', methods=['GET'])
class UserDetail(MethodView):

    @user_blueprint.alt_response(status_code=200,example={"success":True,"message":"User updated","data":{}})
    @jwt_required()
    def get(self,*args,**kwargs):
        result = UserController().user_detail()
        return result

@user_blueprint.route('/update/photo', methods=['POST'])
class UpdateUser(MethodView):

    @user_blueprint.alt_response(status_code=200,example={"success":True,"message":"User photo updated","data":{"photo":""}})
    @jwt_required()
    def post(self,*args,**kwargs):
        result = UserController().update_user_photo(photo=request.files['photo'], user_id=current_user.id)
        return result
    
#endpoints for fetching user list by role
@user_blueprint.route('/dr-list', methods=['GET'])
class DrList(MethodView):
    @user_blueprint.alt_response(status_code=200,example={"success":True,"message":"User list","data":[]})
    def get(self):
        result = UserController().get_dr_list()
        return result

#endpoint for fetching user's location
@user_blueprint.route('/location/<string:lat>/<string:lang>', methods=['GET'])
class UserLocation(MethodView):
    @user_blueprint.alt_response(status_code=200,example={"success":True,"message":"User location","data":[]})
    def get(self,lat,lang):
        result = get_location_from_google_maps(lat=lat,lang=lang)
        return jsonify({"data":result})
