from database.service import db
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, UniqueConstraint, Float
from datetime import datetime, timedelta
from sqlalchemy import JSON
from constants import DEFAULT_MEMBERSHIP_NAME


class MemberShipPlan(db.Model):
    __tablename__ = "membership_plans"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, default=DEFAULT_MEMBERSHIP_NAME, unique=True)
    description = db.Column(db.Text(), nullable=True)
    price = db.Column(db.Float(), nullable=False, default=0)
    validity_in_days = db.Column(db.Integer, nullable=False, default=365)
    config = db.Column(JSON, nullable=True)  # JSON field for configuration data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    user_membership = db.relationship(
        "UserMembership",
        back_populates="membership",
        cascade="all, delete",
        lazy="dynamic",
    )
    user_membership_plan_log = db.relationship(
        "UserMembershipPlanLog",
        back_populates="membership",
        cascade="all, delete",
        lazy="dynamic",
    )
    # users = db.relationship("User", back_populates="membership_plan", cascade="all, delete")
    __table_args__ = (UniqueConstraint("name", name="_membership_plan_name"),)

    def __repr__(self):
        return f"<MemberShipPlan {self.name}>"

    def __str__(self):
        return f"<MemberShipPlan {self.name}>"

    @staticmethod
    def get_all():
        return MemberShipPlan.query.all()

    @staticmethod
    def get_by_id(id):
        return MemberShipPlan.query.get(id)


class UserMembership(db.Model):
    __tablename__ = "user_membership"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    membership_plan_id = db.Column(
        db.Integer, db.ForeignKey("membership_plans.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    validity_till = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    membership = db.relationship("MemberShipPlan", back_populates="user_membership")
    

    __table_args__ = (
        UniqueConstraint("user_id", "membership_plan_id", name="_user_membership"),
        UniqueConstraint("user_id", "is_active", name="_user_active_membership"),
    )

    def __repr__(self):
        return f"<UserMembership {self.id}>"

    def __str__(self):
        return f"<UserMembership {self.id}>"

    def save(self):
        self.current_token_limit = self.membership.config.get("token_limit")
        self.validity_till = datetime.utcnow() + timedelta(
            days=self.membership.validity_in_days
        )
        
        ''' TODO: Add cron job to check validity of membership and update is_active 
        flag and change membership plan to free'''

        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_all():
        return UserMembership.query.all()

    @staticmethod
    def get_users_all_membership(user_id):
        return UserMembership.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_active_membership(user_id):
        return UserMembership.query.filter_by(user_id=user_id, is_active=True).first()


class UserMembershipPlanLog(db.Model):
    __tablename__ = "user_membership_plan_log"
    """ db model for user membership plan log where user can renew or upgrade membership plan"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    membership_plan_id = db.Column(
        db.Integer, db.ForeignKey("membership_plans.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    consumed_tokens = db.Column(db.Integer, default=0)
    current_token_limit = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    membership = db.relationship(
        "MemberShipPlan", back_populates="user_membership_plan_log"
    )
    version = db.Column(db.Integer, default=1)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "membership_plan_id", "version", name="_user_membership_plan"
        ),
    )

    def __repr__(self):
        return f"<UserMembershipPlanLog {self.id}>"
    
    @staticmethod
    def get_remaining_tokens(self, user_id):
        """Returns remaining tokens of user by version."""
        existing_log: UserMembershipPlanLog = (
            UserMembershipPlanLog.get_latest_membership_plan(user_id)
        )
        return existing_log.current_token_limit - existing_log.consumed_tokens

    @staticmethod
    def add_consumed_tokens(self, user_id, tokens_consumed):
        """Add consumed tokens to the log to latest version of membership plan"""
        existing_log: UserMembershipPlanLog = (
            UserMembershipPlanLog.get_latest_membership_plan(user_id)
        )
        existing_log.consumed_tokens += tokens_consumed
        db.session.add(existing_log)
        db.session.commit()

    @staticmethod
    def get_latest_membership_plan(self, user_id):
        """Returns the latest membership plan of user by version."""
        return (
            UserMembershipPlanLog.query.filter_by(user_id=user_id)
            .order_by(UserMembershipPlanLog.version.desc())
            .first()
        )
