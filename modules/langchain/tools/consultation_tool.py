from flask import current_app
from langchain.tools import StructuredTool
from functools import partial
from langchain_core.tools import ToolException

from application.schemas.topic_feedback_schemas import SupervisorFeedbackSchema
from application.schemas.topic_schema import TopicSchema
from database.service import db
from application.models.topicModel import Topic
from application.models.customMessage import SupervisorFeedback
import json
from application.controllers.chat.models import Consultation, ConsultationType
from services.socket.actions import ACTIONS
from services.socket.socket import socketio


def consult_healthcare_professional(
        consultation_type: str = ConsultationType.not_decided,
        symptoms: str = "",
        symptoms_clarifying_questions_answers: list = [],
        contact_information_question_and_answers: list = [],
        medical_history_and_life_style_question_and_answers: list = [],
        tentative_diagnosis: str = "Not Diagnosed",
        doctor_name: str = "",
        topic_id: int = None
) -> str:
    """
    Calls healthcare professional with the given information

    """

    if not all([symptoms, contact_information_question_and_answers]):
        if not symptoms:
            raise ToolException("symptoms are needed before calling Supervisor or healthcare professional")

        elif not contact_information_question_and_answers:
            raise ToolException("Need to gather user's basic contact information. Example: Name, Age, Mobile Number")

    print("topic_id from consultation tool", topic_id)

    pre_screening_question_and_answers = []
    pre_screening_question_and_answers.append({"Consultation Type": consultation_type})
    pre_screening_question_and_answers.extend(symptoms_clarifying_questions_answers)
    pre_screening_question_and_answers.extend(contact_information_question_and_answers)
    pre_screening_question_and_answers.extend(medical_history_and_life_style_question_and_answers)

    feedback = send_data_to_consultation(symptoms, pre_screening_question_and_answers, tentative_diagnosis,
                                         consultation_type, topic_id)
    if feedback:
        return "consultation tool executed. I am informed successfully with the given information and this chat has been ended."
    else:
        return "failed with the given information"
        # return "Failed to inform healthcare professional with the given information"


def _handle_error(error: ToolException) -> str:
    """Handles errors thrown by the supervisor call tool."""
    current_app.logger.info(str(error))
    return f"{str(error)}"


def send_data_to_consultation(symptoms: str, pre_screening_question_and_answers: list, tentative_diagnosis: str,
                              consultation_type: str, topic_id: int):
    """
    Put entry in supervisor_feedback table

    Args:
    notes: str (notes from patient's chat conversation)
    topic_id: int (topic id of the conversation)

    Returns:
    bool: True if entry is added successfully else False
    """
    try:

        topic: Topic = Topic.query.filter_by(id=topic_id).first()
        if topic:
            feedback = (
                db.session.query(SupervisorFeedback)
                .filter(SupervisorFeedback.topic_id == topic_id)
                .first()
            )
            if feedback:
                feedback.notes = json.dumps(
                    {"symptoms": symptoms, "pre_screening_question_and_answers": pre_screening_question_and_answers,
                     "tentative_diagnosis": tentative_diagnosis, "consultation_type": consultation_type})
            else:
                feedback = SupervisorFeedback(topic_id=topic_id, notes=json.dumps(
                    {"symptoms": symptoms, "pre_screening_question_and_answers": pre_screening_question_and_answers,
                     "tentative_diagnosis": tentative_diagnosis, "consultation_type": consultation_type}))
                db.session.add(feedback)
                db.session.flush()

            if consultation_type == ConsultationType.in_person:
                topic.ended = True
                socketio.emit(f"agent/{topic.user_id}", {"action": ACTIONS['topic_ended'],
                                                         "data": {'topic': TopicSchema(many=False).dump(topic)}})

            # emitting to user
            socketio.emit(f"feedback", {"data": {"topic": SupervisorFeedbackSchema(many=False).dump(feedback),
                                                 "summary": json.dumps({"symptoms": symptoms,
                                                                        "pre_screening_question_and_answers": pre_screening_question_and_answers,
                                                                        "tentative_diagnosis": tentative_diagnosis,
                                                                        "consultation_type": consultation_type})},
                                        "action": ACTIONS['feedback']})
            db.session.commit()
            return feedback
        else:
            return None
    except Exception as e:
        current_app.logger.info(str(e))
        return None


def consult_healthcare_professional_wrapper(topic_id, *args, **kwargs):
    """
    Wrapper function to include topic_id directly into the function arguments,
    bypassing the need to inject it into the schema.
    """
    return consult_healthcare_professional(*args, **kwargs, topic_id=topic_id)


def get_consultation_tool(topic_id):
    """
    Returns a StructuredTool configured with a wrapped function that has topic_id set.
    """
    # Create a partial function with topic_id preset
    wrapped_function = partial(consult_healthcare_professional_wrapper, topic_id)

    return StructuredTool.from_function(
        wrapped_function,
        name="consultation_tool",
        description="Useful in case of consulting healthcare professional, setting up in person or telephonic or emergency consultation",
        args_schema=Consultation,  # Use the original Consultation schema without topic_id
        return_direct=False,
        handle_tool_error=_handle_error,
    )
