import logging
from langchain.tools import BaseTool, StructuredTool
from typing import Optional
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import ToolException
from database.service import db
from application.models.topicModel import Topic
from application.models.customMessage import CustomMessage, SupervisorFeedback
import json


class SupervisorCall(BaseModel):
    """Supervisor call model with required fields and an optional reason."""

    symptoms: str = Field(default="", description="Symptoms of the patient") 
    pre_screening_question_and_answers: list = Field(
        default =[], description="Pre screening questions and answers"
    )
    follow_up_questions_answers: Optional[list] = Field(
        [], description="Follow up questions and answers"
    )
    tentative_diagnosis: str = Field(
        default="Not Diagnosed", description="Tentative diagnosis of the patient"
    )

    class Config:
        schema_extra = {
            "example": {
                "symptoms": "frequent urinal problem, frequent hunger & thirst",
                "pre_screening_question_and_answers": [
                    {"Do you have a fever?": "No"},
                    {"Do you have a cough?": "No"},
                ],
                "follow_up_questions_answers": [
                    {"Do you have a fever?": "No"},
                    {"Do you have a cough?": "No"},
                ],
                "tentative_diagnosis": "Diabetes type 2",
            }
        }


def call_supervisor(symptoms: str = "", pre_screening_question_and_answers: list = [], follow_up_questions_answers: list = [], tentative_diagnosis: str = "") -> str:
    '''
    Informing supervisor or healthcare professional to get feedback
    '''
    if not all([symptoms, pre_screening_question_and_answers, tentative_diagnosis]):
        if not symptoms:
            raise ToolException("symptoms are needed  to call Supervisor or healthcare professional")
        elif not pre_screening_question_and_answers:
            raise ToolException("pre_screening_question_and_answers is needed to call Supervisor or healthcare professional")
        # elif not tentative_diagnosis:
        #     raise ToolException("Tentative diagnosis is needed to call Supervisor or healthcare professional ")
        

    return "Supervisor or healthcare professional is informed successfully with the given information and this chat has been ended"


def _handle_error(error: ToolException) -> str:
    """Handles errors thrown by the supervisor call tool."""
    print("An error occurred:", error)
    return error


class SupervisorDataHandler:
    @staticmethod
    def send_data_to_supervisor(patient_summery: str, topic_id: int) -> bool:
        """
        Put entry in supervisor_feedback table

        Args:
        notes: str (notes from patient's chat conversation)
        topic_id: int (topic id of the conversation)

        Returns:
        bool: True if entry is added successfully else False
        """
        try:
            if isinstance(patient_summery, str):
                patient_summery_data = json.loads(patient_summery)
                print("patient_summery is str")
            elif isinstance(patient_summery, dict):
                patient_summery_data = patient_summery
                print("patient_summery is dict")
            print("patient summery", patient_summery_data)
            print("patient summery symptoms", patient_summery_data.get("symptoms"))
            #first check if patient_summery has all the required fields such as symptoms, pre_screening_question_and_answers, tentative_diagnosis
            if not all([patient_summery_data.get("symptoms"), patient_summery_data.get("pre_screening_question_and_answers"), patient_summery_data.get("tentative_diagnosis")]):
        
                if not patient_summery_data.get("symptoms"):
                    raise ToolException("symptoms are needed to call Supervisor or healthcare professional")
                elif not patient_summery_data.get("pre_screening_question_and_answers"):
                    raise ToolException("pre_screening_question_and_answers is needed to call Supervisor or healthcare professional")
                # elif not patient_summery_data.get("tentative_diagnosis"):
                #     raise ToolException("Tentative diagnosis is needed to call Supervisor or healthcare professional ")
            
            topic = db.session.query(Topic).filter(Topic.id == topic_id).first()
            if topic:
                #convert patient_summery to json
                print("patient_summery", patient_summery, "type", type(patient_summery))
                patient_summery = json.dumps(patient_summery)

                feedback = (
                    db.session.query(SupervisorFeedback)
                    .filter(SupervisorFeedback.topic_id == topic_id)
                    .first()
                )
                if feedback:
                    feedback.notes = patient_summery
                else:
                    feedback = SupervisorFeedback(topic_id=topic_id, notes=patient_summery)
                    db.session.add(feedback)

                topic.ended = True
                db.session.commit()
                return feedback
            else:
                return None
        except Exception as e:
            print("An error occurred:", e)
            return None


# Tool for calling supervisor
call_supervisor_tool = StructuredTool.from_function(
    call_supervisor,
    name="call_supervisor",
    description="Useful for calling healthcare professional or supervisor",
    args_schema=SupervisorCall,
    return_direct=False,
    handle_tool_error=_handle_error,
)
