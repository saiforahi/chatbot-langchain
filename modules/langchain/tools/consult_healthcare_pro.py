import logging
from langchain.tools import BaseTool, StructuredTool
from typing import Optional
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import ToolException
from database.service import db
from application.models.topicModel import Topic
from application.models.customMessage import CustomMessage, SupervisorFeedback
import json


class HealthCareProfessionalCall(BaseModel):
    """Healthcare professional call model with required fields and an optional reason."""

    symptoms: str = Field(default="", description="Symptoms of the patient") 

    symptoms_clarifying_questions_answers: list = Field(
        [], description="Symptoms clarifying questions and answers"
    )
    personal_information_question_and_answers: list = Field(
        default =[], description="Basic Personal information questions and answers (Example: age, name, medical history) "
    )
    medical_history_and_life_style_question_and_answers: list = Field(
        default =[], description="Medical history and life style assessment questions and answers"
    )
    tentative_diagnosis: str = Field(
        default="Not Diagnosed", description="Tentative diagnosis of the patient along with suggested medical tests if any"
    )
    class Config:
        schema_extra = {
            "example": {
                "symptoms": "frequent urinal problem, frequent hunger & thirst",
                "symptoms_clarifying_questions_answers": [
                    {"How long have you been experiencing frequent urination?": "2 weeks"},
                    {"How often do you feel hungry?": "every 2 hours"},
                    {"How often do you feel thirsty?": "every 30 minutes"},
                ],
                
                "personal_information_question_and_answers": [
                    {"What is your age?": "25"},
                    {"What is your Full Name?": "John Doe"},
                    {"do you have any allergies?": "No"},
                ],
               "medical_history_and_life_style_question_and_answers": [
                    {"Do you have a family history of diabetes?": "Yes"},
                    {"Do you smoke?": "No"},
                    {"Do you drink alcohol?": "No"},
                ],
                "tentative_diagnosis": "Diabetes type 2, suggested medical tests: Fasting blood sugar, HbA1c, Urine test"
            }

        }



def consult_healthcare_professional(
    symptoms: str,
    symptoms_clarifying_questions_answers: list,
    personal_information_question_and_answers: list,
    medical_history_and_life_style_question_and_answers: list,
    tentative_diagnosis: str,
) -> str:
    """
    Calls supervisor or healthcare professional with the given information

    Args:
    symptoms: str (symptoms of the patient)
    symptoms_clarifying_questions_answers: list (symptoms clarifying questions and answers)
    personal_information_question_and_answers: list (Basic Personal information questions and answers (Example: age, name, medical history))
    medical_history_and_life_style_question_and_answers: list (Medical history and life style assessment questions and answers)
    tentative_diagnosis: str (Tentative diagnosis of the patient along with suggested medical tests if any)

    Returns:
    str: Supervisor or healthcare professional is informed successfully with the given information and this chat has been ended
    """
    
    #check if all the required fields are present
    if not all([symptoms, symptoms_clarifying_questions_answers, personal_information_question_and_answers, medical_history_and_life_style_question_and_answers, tentative_diagnosis]):
        if not symptoms:
            raise ToolException("symptoms are needed before calling Supervisor or healthcare professional")
        elif not symptoms_clarifying_questions_answers:
            raise ToolException("To call Supervisor or healthcare professional , we need more information to gather sequentially. Gradually, has to EXECUTE `STEP 2: Symptoms and Concern Clarification`, `STEP 3: Medical History & Lifestyle Assessment`, `STEP 4: Asking for Basic Personal Information` ", )
        elif not medical_history_and_life_style_question_and_answers:
            raise ToolException("we need more information before moving. Gradually, need to ask Medical History & Lifestyle Assessment , Basic Personal Information`")
        elif not personal_information_question_and_answers:
            raise ToolException("To call Supervisor or healthcare professional , we need more information to gather sequentially. Gradually, Has to EXECUTE `STEP 4: Asking for Basic Personal Information`")
       
        # elif not tentative_diagnosis:
        #     raise ToolException("Tentative diagnosis is needed to call Supervisor or healthcare professional ")
    
    return "Supervisor or healthcare professional is informed successfully with the given information and this chat has been ended"


def _handle_error(error: ToolException) -> str:
    """Handles errors thrown by the supervisor call tool."""
    print("An error occurred:", error)
    return f"{str(error)}"


class HealthCareProfessionalDataHandler:
    @staticmethod
    def send_data_to_professional(patient_summery: str, topic_id: int) -> bool:
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
            if not all([patient_summery_data.get("symptoms"), patient_summery_data.get("symptoms_clarifying_questions_answers"), patient_summery_data.get("personal_information_question_and_answers"), patient_summery_data.get("tentative_diagnosis")]):
    
                if not patient_summery_data.get("symptoms"):
                    raise ToolException("symptoms are needed to call Supervisor or healthcare professional")
                elif not patient_summery_data.get("symptoms_clarifying_questions_answers"):
                        raise ToolException("To call Supervisor or healthcare professional , we need more information to gather sequentially. Gradually, has to EXECUTE `STEP 2: Symptoms and Concern Clarification`, `STEP 3: Medical History & Lifestyle Assessment`, `STEP 4: Asking for Basic Personal Information` ", )
                elif not patient_summery_data.get("personal_information_question_and_answers"):
                    raise ToolException("To call Supervisor or healthcare professional , we need more information to gather sequentially. Gradually, Has to EXECUTE `STEP 4: Asking for Basic Personal Information`")
                # elif not patient_summery_data.get("tentative_diagnosis"):
                #     raise ToolException("Tentative diagnosis is needed to call Supervisor or healthcare professional ")
            
            patient_summery_data["pre_screening_question_and_answers"] = []
            patient_summery_data["pre_screening_question_and_answers"].extend(patient_summery_data["symptoms_clarifying_questions_answers"])
            patient_summery_data["pre_screening_question_and_answers"].extend(patient_summery_data["personal_information_question_and_answers"])
            patient_summery_data["pre_screening_question_and_answers"].extend(patient_summery_data["medical_history_and_life_style_question_and_answers"])
            
            topic = db.session.query(Topic).filter(Topic.id == topic_id).first()
            if topic:
                #convert patient_summery to json
                print("patient_summery", patient_summery, "type", type(patient_summery))
                patient_summery = json.dumps(patient_summery)
                # #add personal_information_question_and_answers to pre_screening_question_and_answers
                # patient_summery_data["pre_screening_question_and_answers"].extend(patient_summery_data["personal_information_question_and_answers"])

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
consult_professional_tool = StructuredTool.from_function(
    consult_healthcare_professional,
    name="consult_healthcare_professional",
    description="Useful for consulting healthcare professional or supervisor",
    args_schema=HealthCareProfessionalCall,
    return_direct=False,
    handle_tool_error=_handle_error,
)
