from flask import request
from application.controllers.baseController import BaseController
from application.models.memberShipModels import (
    UserMembership,
    UserMembershipPlanLog,
    MemberShipPlan,
)
from application.schemas.user_membership_schema import (
    UserMembershipSchema,
    UserMembershipCreateSchema,
)
from database.service import db
from datetime import datetime, timedelta
from application.controllers.utils import encode_user_details
from flask_jwt_extended import current_user


class UserMembershipController(BaseController):
    def create_membership(self, user_id, data):
        try:
            # first check if user already has a membership
            membership = UserMembership.query.filter_by(
                user_id=user_id, is_active=True
            ).first()
            if membership:
                print("current_user", current_user)
                 
                return self.error_response(
                    message="User already has a active membership, You either need to renew or upgrade the existing membership"
                )
            # membership_token = encode_user_details(
            #     current_user.email, current_user.first_name
            # )
            
            # create new membership

            new_membership = UserMembership(
                user_id=user_id,
                membership_plan_id=data["membership_plan_id"],
                is_active=data.get("is_active", True),
                # membership_token=membership_token,
            )
            # also create new instance at membership plan log
            new_membership_plan_log = UserMembershipPlanLog(
                user_id=user_id,
                membership_plan_id=data["membership_plan_id"],
                # curren token limit from membership plan config json field
                current_token_limit=MemberShipPlan.query.filter_by(
                    id=data["membership_plan_id"]
                )
                .first()
                .config.get("token_limit", 0),
            )
            db.session.add(new_membership)
            db.session.add(new_membership_plan_log)

            db.session.commit()
            return self.success_response(
                message="Membership created successfully",
                data=UserMembershipSchema().dump(new_membership),
            )
        except Exception as e:
            return self.error_response(
                message="Membership creation failed", errors=str(e)
            )

    def get_membership(self, user_id):
        try:
            membership = UserMembership.query.filter_by(
                user_id=user_id, is_active=True
            ).first()
            if not membership:
                return self.error_response(message="Membership not found")
            data = UserMembershipSchema().dump(membership)
            return self.success_response(message="Membership details", data=data)
        except Exception as e:
            return self.error_response(message="Membership fetch failed", errors=str(e))

    def update_membership(self, user_id, data):
        try:
            membership = UserMembership.query.filter_by(
                user_id=user_id, is_active=True
            ).first()
            if not membership:
                return self.error_response(message="Membership not found")

            membership.membership_plan_id = data.get(
                "membership_plan_id", membership.membership_plan_id
            )
            membership.is_active = data.get("is_active", membership.is_active)
            db.session.commit()

            return self.success_response(
                message="Membership updated successfully",
                data=UserMembershipSchema().dump(membership),
            )
        except Exception as e:
            return self.error_response(
                message="Membership update failed", errors=str(e)
            )

    def delete_membership(self, user_id):
        try:
            membership = UserMembership.query.filter_by(
                user_id=user_id, is_active=True
            ).first()
            if not membership:
                return self.error_response(message="Membership not found")

            db.session.delete(membership)
            db.session.commit()

            return self.success_response(
                message="Membership deleted successfully",
                data=UserMembershipSchema().dump(membership),
            )
        except Exception as e:
            return self.error_response(
                message="Membership delete failed", errors=str(e)
            )

    def renew_membership(self, user_id):
        """
        This method will renew the membership of user;
        1. Set validity till to current date time + membership validity in days
        2. Set is_active to True
        3. Create new instance at membership plan log with current token limit and increment version number

        args:
            user_id: int
        return:
            success response

        """
        try:
            user_membership: UserMembership = UserMembership.query.filter_by(
                user_id=user_id, is_active=True
            ).first()
            membership: MemberShipPlan = user_membership.membership
            if not user_membership:
                return self.error_response(message="Membership not found")
            # set validity till to current date time + membership validity in days
            user_membership.validity_till = datetime.utcnow() + timedelta(
                days=membership.validity_in_days
            )
            user_membership.updated_at = datetime.utcnow()
            user_membership.is_active = True
            user_membership.save()
            # also create new instance at membership plan log with current token limit and increment version number
            old_membership_plan_log: UserMembershipPlanLog = (
                UserMembershipPlanLog.query.filter_by(
                    user_id=user_id, version=user_membership.version
                ).first()
            )
            new_membership_plan_log: UserMembershipPlanLog = UserMembershipPlanLog(
                user_id=user_id,
                membership_plan_id=user_membership.membership_plan_id,
                # curren token limit from membership plan config json field
                current_token_limit=MemberShipPlan.query.filter_by(
                    id=user_membership.membership_plan_id
                )
                .first()
                .config.get("token_limit", 0),
                version=old_membership_plan_log.version + 1,
            )
            db.session.add(new_membership_plan_log)

            db.session.commit()

            return self.success_response(
                message="Membership renewed successfully",
                data=UserMembershipSchema().dump(user_membership),
            )
        except Exception as e:
            return self.error_response(message="Membership renew failed", errors=str(e))

    def upgrade_membership(self, user_id, data):
        """
        if the user has a active membership, then make it inactive and create new membership with new membership plan
        and set is_active to True
        args:
            user_id: int
            data: dict
        return:
            success response

        """

        try:
            old_membership: UserMembership = UserMembership.query.filter_by(
                user_id=user_id, is_active=True
            ).first()

            if not old_membership:
                return self.error_response(
                    message="No active membership found to upgrade"
                )
            # set is_active to False
            old_membership.is_active = False
            old_membership.updated_at = datetime.utcnow()
            old_membership.save()
            # create new membership with new membership plan and set is_active to True
            new_membership = UserMembership(
                user_id=user_id,
                membership_plan_id=data["membership_plan_id"],
                is_active=True,
            )
            # also create new instance at membership plan log
            new_membership_plan_log = UserMembershipPlanLog(
                user_id=user_id,
                membership_plan_id=data["membership_plan_id"],
                # curren token limit from membership plan config json field
                current_token_limit=MemberShipPlan.query.filter_by(
                    id=data["membership_plan_id"]
                )
                .first()
                .config.get("token_limit", 0),
            )
            db.session.add(new_membership)
            db.session.add(new_membership_plan_log)

            db.session.commit()
            return self.success_response(
                message="Membership upgraded successfully",
                data=UserMembershipSchema().dump(new_membership),
            )
        except Exception as e:
            return self.error_response(
                message="Membership upgrade failed", errors=str(e)
            )
