from flask import current_app
from langchain.tools import StructuredTool
from functools import partial
from langchain_core.tools import ToolException
from database.service import db
import json
from application.controllers.chat.models import DoctorSuggestion
from sqlalchemy.sql import text
from constants import DOCTOR_SPECIALIZATION

from sqlalchemy.sql import text
import json
from modules.langchain.tools.doctor_helpers import search_doctors_by_proximity
from application.helper import get_lat_long_from_google_maps


def find_nearby_doctors(
        Doctor_FieldsOfMedicine=[],
        Doctor_Professions=[],
        Doctor_Descriptors=[],
        Doctor_Medical_FieldKeywords=[],
        Human_Readable_Precise_Location="",
        language: str = "English",
) -> str:
    """Suggests nearby doctors based on specialization and user location."""
    user_lat, user_long = None, None
    current_app.logger.info(f"human readable precise location:{Human_Readable_Precise_Location}")
    current_app.logger.info(f"is human readable location true?:{Human_Readable_Precise_Location == True}")

    if Human_Readable_Precise_Location:

        lat_long_from_google_map = get_lat_long_from_google_maps(Human_Readable_Precise_Location)
        current_app.logger.info(f"lat_long_from_google_map:{lat_long_from_google_map}")

        if lat_long_from_google_map:
            user_lat = lat_long_from_google_map.get("lat")
            user_long = lat_long_from_google_map.get("lng")
    else:
        raise ToolException("Could you please let me know your more precise location?")

    if (
            Doctor_FieldsOfMedicine
            or Doctor_Professions
            or Doctor_Descriptors
            or Doctor_Medical_FieldKeywords
    ):
        specialization_search_terms = {}
        regex_search_items_as_a_world = []
        regex_search_items_as_prefix = []

        regex_search_items_as_a_world.extend(
            Doctor_FieldsOfMedicine
        )
        regex_search_items_as_a_world.extend(
            Doctor_Professions
        )
        regex_search_items_as_prefix.extend(
            Doctor_Descriptors
        )
        regex_search_items_as_prefix.extend(
            Doctor_Medical_FieldKeywords
        )

        specialization_search_terms["regex_search_items_as_a_world"] = regex_search_items_as_a_world
        specialization_search_terms["regex_search_items_as_prefix"] = regex_search_items_as_prefix

        current_app.logger.info(f"final lat long {user_lat}, {user_long}")
        return search_doctors_by_proximity(
            user_lat, user_long, language, specialization_search_terms
        )
    else:
        return search_doctors_by_proximity(user_lat, user_long, language)


def _handle_error(error: ToolException) -> str:
    """Handles errors thrown by the tool"""
    current_app.logger.info(str(error))
    return f"{str(error)}"


def doctor_suggestions_wrapper(language, *args, **kwargs):
    """
    Wrapper function to include topic_id directly into the function arguments,
    bypassing the need to inject it into the schema.
    """
    return find_nearby_doctors(*args, **kwargs, language=language)


def get_doctor_suggestions_tool(language):
    """
    Returns a StructuredTool configured with a wrapped function that has user_lat and user_long preset.
    """
    # Create a partial function with topic_id preset
    wrapped_function = partial(doctor_suggestions_wrapper, language)
    # Create a tool with the wrapped function
    tool = StructuredTool.from_function(
        wrapped_function,
        name="suggest_nearby_doctors",
        description="Suggests specialized doctors or healthcare professionals to the user specializing in the user's health concerns",
        return_direct=True,
        handle_tool_error=_handle_error,
        args_schema=DoctorSuggestion,
    )
    return tool
