from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from database.service import db
from enum import Enum
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import SQLAlchemyError


class Road_Map_Status(Enum):
    NOT_APPROVED = "not_approved"
    IDEA = "idea"
    NEXT_IN_LINE = "next_in_line"
    SHIPPED = "shipped"

    def __str__(self):
        return self.value


class Road_Map_Key(Enum):
    COMMENT = "comment"
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"

    def __str__(self):
        return self.value


class Roadmap(db.Model):
    __tablename__ = "road_maps"
    id = db.Column(Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    # status a enum; default: pending
    status = db.Column(db.Enum(Road_Map_Status), default=Road_Map_Status.NOT_APPROVED.value)
    created_at = db.Column(DateTime, default=datetime.now())
    updated_at = db.Column(DateTime, default=datetime.now(), onupdate=datetime.now())

    def __repr__(self):
        return "<Roadmap %r>" % self.id

    def __str__(self):
        return "<Roadmap %r>" % self.id

    def upvote_count(self):
        return RoadmapFeedback.query.filter_by(
            road_map_id=self.id, key=Road_Map_Key.UPVOTE.value).count()

    def downvote_count(self):
        return RoadmapFeedback.query.filter_by(
            road_map_id=self.id, key=Road_Map_Key.DOWNVOTE.value).count()

    def comments(self):
        return RoadmapFeedback.query.filter_by(
            road_map_id=self.id, key=Road_Map_Key.COMMENT.value).all()


class RoadmapFeedback(db.Model):
    __tablename__ = "road_map_feedbacks"
    id = db.Column(Integer, primary_key=True)
    road_map_id = db.Column(db.Integer, db.ForeignKey(Roadmap.id), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    key = db.Column(db.Enum(Road_Map_Key), nullable=False)
    value = db.Column(
        db.Text(), nullable=True
    )  # Stores either comment text or '1'for votes

    created_at = db.Column(DateTime, default=datetime.now())
    updated_at = db.Column(DateTime, default=datetime.now(), onupdate=datetime.now())

    def __repr__(self):
        return "<RoadmapFeedback %r>" % self.id

    def __str__(self):
        return "<RoadmapFeedback %r>" % self.id

    @staticmethod
    def create_or_update(road_map_id, user_id, key, value):
        """
        if key is comment, then value is comment text, and user can make multiple comments,
        but if key is upvote or downvote, then value is 1, and user can only make one vote,
        if user has already voted, then update the vote,
        else create a new vote
        """
        try:
            if key == Road_Map_Key.COMMENT.value:
                
                print("Road_Map_Key.COMMENT", Road_Map_Key.COMMENT)
                print("key", key)
                # create a new comment
                comment = RoadmapFeedback(
                    road_map_id=road_map_id, user_id=user_id, key=key, value=value
                )
                print(comment.value)
                db.session.add(comment)
                db.session.commit()
                return comment, None
            else:
                # Convert value to boolean for votes
                vote_value = value == "1"
                # check if user has already voted
                vote: RoadmapFeedback = (
                    RoadmapFeedback.query.filter_by(
                        road_map_id=road_map_id, user_id=user_id
                    )
                    .filter(
                        RoadmapFeedback.key.in_(
                            [Road_Map_Key.UPVOTE.value, Road_Map_Key.DOWNVOTE.value]
                        )
                    )
                    .first()
                )
                if vote:
                    vote.key = key  # Update vote type if it has changed
                    vote.value = vote_value
                    db.session.commit()
                    return vote, None
                else:
                    # create a new vote
                    vote = RoadmapFeedback(
                        road_map_id=road_map_id,
                        user_id=user_id,
                        key=key,
                        value=vote_value,
                    )
                    db.session.add(vote)
                    db.session.commit()
                    return vote, None
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def undo_vote(road_map_id, user_id):
        """Remove a user's vote from a roadmap item."""
        try:
            vote = (
                RoadmapFeedback.query.filter_by(
                    road_map_id=road_map_id, user_id=user_id
                )
                .filter(
                    RoadmapFeedback.key.in_(
                        [Road_Map_Key.UPVOTE.value, Road_Map_Key.DOWNVOTE.value]
                    )
                )
                .first()
            )

            if vote:
                db.session.delete(vote)
                db.session.commit()
                return True, "Vote removed"
            else:
                return False, "No vote to remove"

        except SQLAlchemyError as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def delete_comment(comment_id, user_id):
        """Delete a specific comment made by a user."""
        try:
            comment = RoadmapFeedback.query.filter_by(
                id=comment_id, user_id=user_id, key=Road_Map_Key.COMMENT.value
            ).first()

            if comment:
                db.session.delete(comment)
                db.session.commit()
                return True, "Comment deleted"
            else:
                return False, "Comment not found or user mismatch"

        except SQLAlchemyError as e:
            db.session.rollback()
            return False, str(e)
