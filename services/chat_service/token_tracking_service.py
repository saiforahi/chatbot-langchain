from application.models.memberShipModels import UserMembership, MemberShipPlan
from application.models.token_tracking_model import TokenTracking
from application.models.chatbotModel import Chatbot
from application.models.chatbotModel import Llm
import logging


class NoActiveMembershipException(Exception):
    pass


class TokenTrackingService:
    """
    This class is responsible for tracking the tokens consumed by the user
    """

    def __init__(self, chatbot: Chatbot, input_tokens: int, output_tokens: int):
        """
        Initializes the TokenTrackingService instance.

        Args:
            chatbot (Chatbot): The Chatbot instance.
            input_tokens (int): The initial input tokens.
            output_tokens (int): The initial output tokens.
        """
        self.chatbot = chatbot
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

        self.logger = logging.getLogger(__name__)

    def get_current_membership(self, user_id) -> MemberShipPlan:
        """
        Returns the current membership of the user.

        Args:
            user_id (int): The user ID.

        Returns:
            MembershipPlan: The current membership of the user.
        """
        user_membership = UserMembership.get_active_membership(user_id)
        if user_membership:
            return user_membership.membership
        raise NoActiveMembershipException("User does not have an active membership")

    def save(self, topic_id, user_id) -> None:
        """
        Saves the token tracking for the user.

        Args:
            topic_id (int): The ID of the topic.
            user_id (int): The ID of the user.
        """
        try:
            llm: Llm = self.chatbot.llm
            token_tracking = TokenTracking.get_by_user_id_topic_id(user_id, topic_id)

            if token_tracking:
                self.update_existing_token_tracking(token_tracking, llm)
            else:
                self.create_new_token_tracking(topic_id, user_id, llm)
        except Exception as e:
            
            self.logger.error(e)
            raise e

    def update_existing_token_tracking(
        self, token_tracking: TokenTracking, llm: Llm
    ) -> None:
        """
        Updates the existing token tracking for the user
        args:
            token_tracking: TokenTracking
            llm: Llm
        returns:
            None

        """
        (
            token_tracking.input_tokens,
            token_tracking.output_tokens,
        ) = self.get_total_tokens(token_tracking)

        token_tracking.price_at_consumption = llm.per_token_cost
        token_tracking.save()

    def create_new_token_tracking(self, topic_id, user_id, llm: Llm) -> None:
        """
        Creates a new token tracking for the user.

        Args:
            topic_id (int): The ID of the topic.
            user_id (int): The ID of the user.
            llm (Llm): The Llm instance.
        """
        TokenTracking(
            user_id=user_id,
            topic_id=topic_id,
            membership_plan_id=self.get_current_membership(user_id).id,
            price_at_consumption=llm.per_token_cost,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        ).save()

    def get_total_tokens(self, token_tracking: TokenTracking) -> tuple[int, int]:
        """
        Returns the total tokens consumed by the user for the topic.

        Args:
            token_tracking (TokenTracking): The token tracking instance.

        Returns:
            Tuple[int, int]: A tuple containing input_tokens and output_tokens.
        """
        input_tokens = token_tracking.input_tokens + self.input_tokens
        output_tokens = token_tracking.output_tokens + self.output_tokens
        return input_tokens, output_tokens
