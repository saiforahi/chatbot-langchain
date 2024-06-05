from flask import Flask, request, jsonify
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.sql import text
from application.schemas.application_schemas import DoctorDataSeedFileSchema
from application.schemas.chatbot_schema import ChatbotFileUploadSchema
from database.service import db
from application.models.doctor_n_others import Chamber, Doctor
from application.models.userModel import User
from application.controllers.doctors.data_seed_controller import DataSeedController
import csv
from werkzeug.security import generate_password_hash
from werkzeug.datastructures import FileStorage

from services.celery.tasks import generate_email_from_name

# Blueprint setup
geo_location_blp = Blueprint(
    "geo_location", __name__, description="Operations on geo location", url_prefix="/api/geo_location"
)

import os
from flask import Flask, request, jsonify, current_app
from werkzeug.utils import secure_filename

@geo_location_blp.route("/seed_data", methods=["POST"])
@geo_location_blp.arguments(DoctorDataSeedFileSchema, location="files")


def seed_data(self, *args, **kwargs):
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        
        upload_folder = os.path.join(current_app.root_path, 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        response = DataSeedController().seed_data_from_csv(file_path)
        
        # delete the file after processing 
        # os.remove(file_path)
        
        return response
#delete seeded data route
@geo_location_blp.route("/delete_seeded_data", methods=["DELETE"])
def delete_seeded_data():
    response = DataSeedController().delete_seeded_data()
    return response

@geo_location_blp.route("/delete_data_from_csv", methods=["DELETE"])
@geo_location_blp.arguments(DoctorDataSeedFileSchema, location="files")
def delete_data(self, *args, **kwargs):
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if file:
            filename = secure_filename(file.filename)
            
            upload_folder = os.path.join(current_app.root_path, 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            with open(file_path, mode="r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for index, row in enumerate(reader):
                    # Use the index to generate the email
                    email = generate_email_from_name(row["name"], index)
                    user = User.query.filter_by(emailOrPhone=email).first()
                    if user:
                        # Retrieve the Doctor ID for deletion criteria in Chamber
                        doctor = Doctor.query.filter_by(user_id=user.id).first()
                        if doctor:
                            # Delete Chamber records first
                            chambers = Chamber.query.filter_by(doctor_id=doctor.id).all()
                            for chamber in chambers:
                                db.session.delete(chamber)
                            
                            # Then delete Doctor record
                            db.session.delete(doctor)

                        # Finally, delete the User record
                        db.session.delete(user)

                    db.session.commit()
                    print(f"Data related to {row['name']} with email {email} deleted successfully")
                print("Data deletion completed successfully")

                return {"success": True, "message": "Data deleted successfully"}
    except Exception as e:
        print(f"Error deleting data: {e}")
        db.session.rollback()
        return {"success": False, "message": "Error deleting data"}
    finally:
        db.session.close()

# def update_doctors_department(csv_file_path):
#     with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
#         reader = csv.DictReader(csvfile)
#         for index, row in enumerate(reader):  # Enumeration to simulate an index
#             # Regenerate the email address using the name and index
#             email = generate_email_from_name(row['name'], index)
#             # Assuming the emailOrPhone field can help identify the corresponding user
#             user = User.query.filter_by(emailOrPhone=email).first()
#             if user:
#                 doctor = Doctor.query.filter_by(user_id=user.id).first()
#                 if doctor:
#                     doctor.department = row['department']  # Ensure 'department' matches CSV column name
#                     db.session.add(doctor)
#                     db.session.flush()
#                     print(f"Updated department for Dr. {row['name']} successfully.")
#                 else:
#                     print(f"No doctor found for user with email {email}.")
#             else:
#                 print(f"No user found with email {email}.")
#         db.session.commit()
#     db.session.close()


# @geo_location_blp.route("/update_departments", methods=["GET"])
# def update_departments():
#     try:
#         # Define the CSV file path here; adjust the path as needed
#         csv_file_path = 'nuanced_bddoctor_latest_final_with_departments.csv'

#         # Call the update function
#         update_doctors_department(csv_file_path)

#         return jsonify({"success": True, "message": "Departments updated successfully"}), 200
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 500
