import os
from flask import current_app
from langchain.tools import StructuredTool
from functools import partial
from langchain_core.tools import ToolException
from database.service import db
import json
from application.controllers.chat.models import DoctorSuggestion, ProjectProposal
from sqlalchemy.sql import text
from constants import DOCTOR_SPECIALIZATION

from sqlalchemy.sql import text
import json
from modules.langchain.tools.doctor_helpers import search_doctors_by_proximity
from application.helper import get_lat_long_from_google_maps

def add_to_proposal(
    title : str,
    name_of_the_section : str,
    content_of_the_section : str,
    topic_id: str,
  
) -> str:
    """Add a new section to a project proposal with open file, save as docx and return the path"""
    try:
        current_app.logger.info(f"topic_id:{topic_id}")
        current_app.logger.info(f"title:{title}")
        current_app.logger.info(f"name_of_the_section:{name_of_the_section}")
        current_app.logger.info(f"content_of_the_section:{content_of_the_section}")
        # Save the section to doc file, add it to trailing part of the proposal and return the path
        with open(f"proposal_{topic_id}.docx", "a") as file:
            if os.path.getsize(f"proposal_{topic_id}.docx") == 0:
                file.write(f"{title}\n\n")
            file.write(f"\n\n{name_of_the_section}\n\n{content_of_the_section}")
            file.close()
        return f"Tool executed. {name_of_the_section} added to proposal, has to move to next section. Call Final Answer Action"
    except Exception as e:
        raise ToolException(f"Error adding section to proposal: {str(e)}")

    


def _handle_error(error: ToolException) -> str:
    """Handles errors thrown by the tool"""
    current_app.logger.info(str(error))
    return f"{str(error)}"


def add_to_proposal_wrapper(topic_id, *args, **kwargs):
    """
    Wrapper function to include topic_id directly into the function arguments,
    bypassing the need to inject it into the schema.
    """
    return add_to_proposal(*args, **kwargs, topic_id=topic_id)


def get_proposal_writer_tool(topic_id):
    """
    Returns a StructuredTool configured with a wrapped function 
    """
    # Create a partial function with topic_id preset
    wrapped_function = partial(add_to_proposal_wrapper, topic_id)
    # Create a tool with the wrapped function
    tool = StructuredTool.from_function(
        wrapped_function,
        name="add_proposal_section_to_doc",
        description="Add a new populated section to the project proposal",
        return_direct=False,
        handle_tool_error=_handle_error,
        args_schema=ProjectProposal,
    )
    return tool
