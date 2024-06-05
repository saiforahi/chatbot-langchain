from enum import Enum
from typing import Optional

from langchain.pydantic_v1 import BaseModel, Field, create_model

from services.socket.actions import ACTIONS
from services.socket.socket import socketio


# from typing import Optional, List


class ConsultationType(str, Enum):
    in_person = "in_person"
    emergency = "emergency"
    telephonic = "telephonic"
    not_decided = "not_decided"


class ProjectProposal(BaseModel):
    """Project proposal schema."""
    title: str = Field(
        default="",
        description="Title of the project proposal"
    )
    name_of_the_section: str = Field(
        default="",
        description="Name of the section of the project proposal"
    )
    content_of_the_section: str = Field(
        default="",
        description="Content of the section of the project proposal"
    )

    class Config:
        schema_extra = {
            "example": {
                "title": "Proposal for the development of a new website",
                "name_of_the_section": "Introduction",
                "content_of_the_section": "This is a proposal for the development of a new website."
            }
        }


class DoctorSuggestion(BaseModel):
    """Doctor suggestion schema."""
    Doctor_FieldsOfMedicine: list[str] = Field(
        default=[],
        description="A comprehensive list of Formal medical specialties or fields, essential for categorizing professionals within the database."
    )
    Doctor_Professions: list[str] = Field(
        default=[],
        description="A comprehensive list of doctor professions related to patient concern"
    )
    Doctor_Descriptors: list[str] = Field(
        default=[],
        description="A comprehensive list of Descriptors and related terms to the Doctor_FieldOfMedicine, broadening search capabilities within the database."
    )
    Doctor_Medical_FieldKeywords: list[str] = Field(
        default=[],
        description="A comprehensive list of associated keywords from various medical fields (e.g., cardio, ortho, dent, physio) instrumental for broad searches."
    )
    Human_Readable_Precise_Location: str = Field(
        default="",
        description="Human readable precise location of user, enhancing the relevance of search results by geographical proximity."
    )

    class Config:
        schema_extra = {
            "example": {
                "Doctor_FieldsOfMedicine": ["cardiology", "orthopedics", "dentistry", "physiotherapy"],
                "Doctor_Professions": ["cardiologist", "orthopedic surgeon", "dentist", "physiotherapist"],
                "Doctor_Descriptors": ["cardiac", "musculoskeletal", "oral", "mental"],
                "Doctor_Medical_FieldKeywords": ["cardio", "ortho", "dent", "physio", "dermatology", "pediatrics",
                                                 "neurology", "psychiatry"],
                "location": {
                    "latitude": "20.378",
                    "longitude": "90.432"
                },
                "Human_Readable_Precise_Location": "Post Office Road, Jhigatola, Dhaka"
            }
        }


class Consultation(BaseModel):
    """ Consultation tool schema """
    consultation_type = ConsultationType = ConsultationType.not_decided

    symptoms: str = Field(default="", description="Symptoms of the patient")

    symptoms_clarifying_questions_answers: list = Field(
        [], description="Symptoms clarifying questions and answers"
    )
    contact_information_question_and_answers: list = Field(
        default=[],
        description="Basic Contact information questions and answers for consultation (Example: name, age, mobile number) "
    )
    medical_history_and_life_style_question_and_answers: list = Field(
        default=[], description="Medical history and life style assessment questions and answers"
    )
    tentative_diagnosis: str = Field(
        default="Not Diagnosed",
        description="Tentative diagnosis of the patient along with suggested medical tests if any"
    )
    doctor_name: str = Field(default="", description="Name of the doctor, patient is interested about")
    doctor_chamber_location: Optional[dict] = Field(
        default={}, description="Latitude and longitude of doctor's chamber"
    )

    class Config:
        schema_extra = {
            "example": {
                "consultation_type": "telephonic|in_person|not_decided|emergency",
                "symptoms": "frequent urinal problem, frequent hunger & thirst",
                "symptoms_clarifying_questions_answers": [
                    {"How long have you been experiencing frequent urination?": "2 weeks"},
                    {"How often do you feel hungry?": "every 2 hours"},
                    {"How often do you feel thirsty?": "every 30 minutes"},
                ],

                "contact_information_question_and_answers": [
                    {"What is your age?": "25"},
                    {"What is your Full Name?": "John Doe"},
                    {"What is your mobile number?": "017XXXXXXXXXXX"},
                ],
                "medical_history_and_life_style_question_and_answers": [
                    {"Do you have a family history of diabetes?": "Yes"},
                    {"Do you smoke?": "No"},
                    {"Do you drink alcohol?": "No"},
                ],
                "tentative_diagnosis": "Diabetes type 2, suggested medical tests: Fasting blood sugar, HbA1c, Urine test",
                "doctor_name": "Dr. John Doe",
                "doctor_chamber_location": {
                    "latitude": "20.378",
                    "longitude": "90.432",
                }
            }
        }