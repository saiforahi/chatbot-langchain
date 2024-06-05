
from flask_jwt_extended import jwt_required
from application.controllers.doctors.doctors_controller import DoctorsController
from flask.views import MethodView
from flask_smorest import Blueprint
from application.schemas.doctor_schemas import DoctorSchema, DoctorCreateSchema

doctors_blp = Blueprint(
    "doctors", __name__, description="Operations on doctors", url_prefix="/api/doctors"
)

@doctors_blp.route("/")
class Doctors(MethodView):

    @doctors_blp.doc(security=[{"BearerAuth": []}])
    @doctors_blp.alt_response(status_code=200, schema=DoctorSchema, example=DoctorSchema.example())
    @jwt_required()
    def get(self):
        return DoctorsController().get_doctors()

@doctors_blp.route("/create")
class CreateDoctor(MethodView):
    @doctors_blp.arguments(schema=DoctorCreateSchema,location="json",example=DoctorCreateSchema.example())
    @doctors_blp.alt_response(status_code=200, schema=DoctorCreateSchema)
    @doctors_blp.doc(security=[{"BearerAuth": []}])
    def post(self, json):
        """Add new doctor"""
        result=DoctorsController().add_doctor(payload=json)
        return result
