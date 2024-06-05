from langchain.tools import BaseTool, StructuredTool
from typing import Optional
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import ToolException


class Appointment(BaseModel):
    """Appointment model with required fields and an optional reason."""
    date: str = Field(..., description="Date of appointment")
    time: str = Field(..., description="Time of appointment")
    doctor: str = Field(..., description="Doctor's name")
    patient: str = Field(..., description="Patient's name")
    reason: Optional[str] = Field(None, description="Reason for the appointment")
    information_provided: bool = Field(False, description="Flag to indicate if all required information is provided")

    class Config:
        schema_extra = {
            "example": {
                "date": "2021-01-01",
                "time": "10:00",
                "doctor": "Dr. Smith",
                "patient": "John Doe",
                "reason": "Checkup",
                "information_provided": True
            }
        }


def book_appointment(
        date: str = "",
        time: str = "",
        doctor: str = "",
        patient: str = "",
        reason: Optional[str] = "",
        information_provided: bool = False,
) -> str:
    """Books an appointment if all required information is provided."""
    if not information_provided or not all([date, time, doctor, patient]):
        raise ToolException(
            "Missing required information for booking the appointment, ask user for the missing information again")

    # Assuming the logic to actually book the appointment goes here
    appointment_details = f"Appointment booked for {patient} with {doctor} on {date} at {time}."
    if reason:
        appointment_details += f" Reason: {reason}."

    with open(f"{patient}_{doctor}_{date}_{time}.txt", "w") as f:
        f.write(appointment_details)

    return appointment_details


def _handle_error(error: ToolException) -> str:
    """Handles errors thrown by the booking tool."""
    return "An error occurred: " + str(error)


appointment_tool = StructuredTool.from_function(
    book_appointment,
    name="book_appointment",
    description="Useful for booking appointments only if you have a doctor's name, patient's name, date, time, and reason.(if information is provided)",
    args_schema=Appointment,
    return_direct=False,
    handle_tool_error=_handle_error,
)
