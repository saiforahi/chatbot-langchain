import json
from sqlalchemy.sql import text

from application.models.doctor_n_others import Doctor, Chamber
from application.models.userModel import User
from database.service import db


def format_doctor_data(doctors_raw):
    structured_docs = []
    unique_sources = set()

    for doctor in doctors_raw:
        # Assuming doctor.chamber_created_at and doctor.chamber_deleted_at are datetime objects or None
        structured_doc = {
            "doctor_id": doctor.doctor_id,
            "lat": doctor.lat,
            "long": doctor.long,
            "address": doctor.address,
            "contact_for_appointment": doctor.contact_no,
            "created_at": doctor.chamber_created_at.isoformat() if doctor.chamber_created_at else None,
            "deleted_at": doctor.chamber_deleted_at.isoformat() if doctor.chamber_deleted_at else None,
            "specializations": doctor.specializations,
            "experiences": doctor.experiences or "",  # Simplify if-check for None or empty string
            "qualifications": doctor.qualifications or "",
            "description": doctor.doctor_description,
            "user_id": doctor.user_id,
            "first_name": doctor.first_name,
            "last_name": doctor.last_name,
            "distance_from_patient_in_m": doctor.distance,
            "distance_from_patient_in_km": f"approx. {doctor.distance / 1000:.2f} km",
            "source_of_reference": doctor.source_of_reference
        }
        structured_docs.append(structured_doc)
        unique_sources.add(doctor.source_of_reference)

    # Sort by distance after structuring docs to keep the operation outside the loop
    sorted_docs = sorted(structured_docs, key=lambda x: x['distance_from_patient_in_m'])

    return sorted_docs, unique_sources


def search_doctors_by_proximity(user_lat, user_long, specialization_search_terms=[]):
    """Searches for nearby doctors, optionally filtering by specialization, qualifications, and description."""
    search_radii = [2000, 4000, 6000]
    like_conditions = []
    parameters = {
        "user_lat": user_lat,
        "user_lon": user_long,
        "search_string": " ".join(specialization_search_terms)
    }
    query = Doctor.search_nearby(lat=parameters['user_lat'],long=parameters['user_lon'],query="Cardiology",radius_in_meters=10000)
    # Chamber.query.join(Chamber.doctor).join(Doctor.user)
    print(query)
    return "hi"


if __name__ == "__main__":
    search_doctors_by_proximity(user_lat=23.822216,user_long=90.433733,specialization_search_terms=['heart','cardiology'])