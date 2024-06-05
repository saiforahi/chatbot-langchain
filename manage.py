# manage.py

from flask.cli import FlaskGroup

from application.models.chatbotModel import Application
from database.service import db
from app import create_app

from application.models.memberShipModels import MemberShipPlan
from application.models.roleModel import Role

app_instance = create_app()
cli = FlaskGroup(create_app=lambda: app_instance)

"""
    This file is used to run the application and to initialize the database.
    To run the application, run the following command:
        python manage.py init-db

"""


@cli.command("init-db")
def init_db():
    """Initialize the database."""
    with app_instance.app_context():
        db.create_all()
        print("Database initialized.")

        # Seed MemberShipPlan
        free_plan = MemberShipPlan(name="Free", price=0, validity_in_days=365)
        db.session.add(free_plan)

        # Seed Role
        user_role = Role(role_name="USER")
        admin_role = Role(role_name="ADMIN")
        dr_role = Role(role_name="DR")

        docadvisor_app=Application(name="docadvisor",domain="docadvisor.xyz")
        db.session.add(user_role)
        db.session.add(admin_role)
        db.session.add(dr_role)

        # Commit changes
        db.session.commit()
        print("Database seeded.")


if __name__ == "__main__":
    cli()
