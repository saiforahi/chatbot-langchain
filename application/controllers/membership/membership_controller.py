# controllers/membershipPlanController.py
from flask import request
from application.controllers.baseController import BaseController
from application.models.memberShipModels import MemberShipPlan
from application.schemas.membership_plan_schema import MemberShipPlanSchema
from database.service import db


class MemberShipPlanController(BaseController):
    def create_plan(self):
        try:
            data = request.get_json()
            plan = MemberShipPlanSchema().load(data)
            new_plan = MemberShipPlan(**plan)
            db.session.add(new_plan)
            db.session.commit()
            return self.success_response(
                message="Plan created successfully",
                data=MemberShipPlanSchema().dump(new_plan),
            )
        except Exception as e:
            return self.error_response(message="Plan creation failed", errors=str(e))

    def get_plan(self, plan_id):
        try:
            plan = MemberShipPlan.query.get(plan_id)
            if not plan:
                return self.error_response(message="Plan not found")
            return self.success_response(data=MemberShipPlanSchema().dump(plan))
        except Exception as e:
            return self.error_response(message="Error fetching plan", errors=str(e))

    def update_plan(self, plan_id):
        try:
            plan = MemberShipPlan.query.get(plan_id)
            if not plan:
                return self.error_response(message="Plan not found")

            data = request.get_json()
            for key, value in data.items():
                setattr(plan, key, value)
            db.session.commit()
            return self.success_response(
                message="Plan updated successfully",
                data=MemberShipPlanSchema().dump(plan),
            )
        except Exception as e:
            return self.error_response(message="Plan update failed", errors=str(e))

    def delete_plan(self, plan_id):
        try:
            plan = MemberShipPlan.query.get(plan_id)
            if not plan:
                return self.error_response(message="Plan not found")
            db.session.delete(plan)
            db.session.commit()
            return self.success_response(message="Plan deleted successfully")
        except Exception as e:
            return self.error_response(message="Plan delete failed", errors=str(e))

    def get_all_plans(self):
        try:
            plans = MemberShipPlan.query.all()
            return self.success_response(
                data=MemberShipPlanSchema(many=True).dump(plans)
            )
        except Exception as e:
            return self.error_response(message="Error fetching plans", errors=str(e))
