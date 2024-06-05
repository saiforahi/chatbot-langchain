# routes/membershipPlanRoutes.py
from flask.views import MethodView
from flask_smorest import Blueprint
from application.controllers.membership.membership_controller import MemberShipPlanController
from application.schemas.membership_plan_schema import (
    MemberShipPlanCreateSchema, 
    MemberShipPlanUpdateSchema, 
    MemberShipPlanResponseSchema
)

membership_plan_blp = Blueprint("membership_plans", "membership_plans", url_prefix="/api/membership_plans")

@membership_plan_blp.route("/")
class MembershipPlanList(MethodView):
    @membership_plan_blp.alt_response(200, MemberShipPlanResponseSchema(many=True))
    def get(self):
        """Get all membership plans"""
        return MemberShipPlanController().get_all_plans()

    @membership_plan_blp.arguments(MemberShipPlanCreateSchema)
    @membership_plan_blp.alt_response(201, MemberShipPlanResponseSchema)
    def post(self, args):
        """Create a new membership plan"""
        return MemberShipPlanController().create_plan()

@membership_plan_blp.route("/<int:plan_id>")
class MembershipPlanDetail(MethodView):
    @membership_plan_blp.alt_response(200, MemberShipPlanResponseSchema)
    def get(self, plan_id):
        """Get a single membership plan"""
        return MemberShipPlanController().get_plan(plan_id)

    @membership_plan_blp.arguments(MemberShipPlanUpdateSchema)
    @membership_plan_blp.alt_response(200, MemberShipPlanResponseSchema)
    def patch(self, args, plan_id):
        """Update a membership plan"""
        return MemberShipPlanController().update_plan(plan_id)

    @membership_plan_blp.response(204)
    def delete(self, plan_id):
        """Delete a membership plan"""
        return MemberShipPlanController().delete_plan(plan_id)
