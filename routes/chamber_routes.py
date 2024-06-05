
from flask_jwt_extended import jwt_required

from application.controllers.doctors.chambers_controller import ChambersController
from application.controllers.doctors.doctors_controller import DoctorsController
from flask.views import MethodView
from flask_smorest import Blueprint
from application.schemas.doctor_schemas import DoctorSchema, ChamberSchema

chambers_blp = Blueprint(
    "chambers", __name__, description="Operations on chambers", url_prefix="/api/chambers"
)


@chambers_blp.route("/")
class Chambers(MethodView):

    @chambers_blp.doc(security=[{"BearerAuth": []}])
    @chambers_blp.alt_response(status_code=200, schema=DoctorSchema, example=DoctorSchema.example())
    @jwt_required()
    def get(self):
        """ get doctor chambers' addresses """
        return ChambersController().get_chamber_plain_list()

@chambers_blp.route("/create")
class ChamberCreate(MethodView):

    @chambers_blp.doc(security=[{"BearerAuth": []}])
    @chambers_blp.arguments(schema=ChamberSchema, location="json", example=ChamberSchema.example())
    @chambers_blp.alt_response(status_code=200, schema=ChamberSchema, example=ChamberSchema.example())
    @jwt_required()
    def post(self,json):
        """ creates doctor chamber """
        return ChambersController().create_doctor_chamber(payload=json)


@chambers_blp.route("/cities-countries")
class CitiesCountries(MethodView):

    # @chambers_blp.doc(security=[{"BearerAuth": []}])
    @chambers_blp.alt_response(status_code=200, example=[{'city':'','country':''}])
    # @jwt_required()
    def get(self):
        """ get doctor chambers' addresses """
        return ChambersController().get_chambers_cities_countries()


