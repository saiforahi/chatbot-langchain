import csv
from flask import current_app, request
from flask_jwt_extended import current_user
from sqlalchemy import func

from application.controllers.baseController import BaseController

from services.celery.tasks import seed_data_from_csv_task
from application.models.doctor_n_others import Doctor, User, Chamber
from database.service import db
from sqlalchemy.exc import OperationalError


class DataSeedController(BaseController):

    def seed_data_from_csv(self, csv_file_path):
        seed_data_from_csv_task.delay(csv_file_path=csv_file_path)
        return self.success_response(message="Data seeding process started")
    
    def delete_seeded_data(self):
        try:
            db.session.autoflush = False  # Disable autoflush
            
            email_pattern = "%@example.com"
            
            # Batch delete function
            def batch_delete(query):
                while True:
                    # Adjust the batch size as necessary
                    batch = query.limit(100).all()
                    if not batch:
                        break
                    for item in batch:
                        db.session.delete(item)
                    try:
                        db.session.commit()
                    except OperationalError as e:
                        db.session.rollback()
                        print(f"OperationalError during batch delete: {e}")
                        raise  # Raising error to exit the function
            
            # Delete chambers in batches
            chamber_query = Chamber.query.join(Doctor, Chamber.doctor_id == Doctor.id).join(User, Doctor.user_id == User.id).filter(User.emailOrPhone.like(email_pattern))
            batch_delete(chamber_query)

            # Delete doctors in batches
            doctor_query = Doctor.query.join(User, Doctor.user_id == User.id).filter(User.emailOrPhone.like(email_pattern))
            batch_delete(doctor_query)

            # Delete users in batches
            user_query = User.query.filter(User.emailOrPhone.like(email_pattern))
            batch_delete(user_query)

            print("Seeded data with email pattern '@example.com' deleted successfully")
            return {"success": True, "message": "Seeded data with email pattern '@example.com' deleted successfully"}
        except Exception as e:
            print(f"Error deleting seeded data with email pattern '@example.com': {e}")
            return {"success": False, "message": f"Error deleting seeded data with email pattern '@example.com': {e}"}
        finally:
            db.session.autoflush = True  # Re-enable autoflush
            db.session.close()