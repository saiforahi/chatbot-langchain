import json

from langchain_core.tools import tool

from application.helper import get_distinct_cities_countries


@tool
def get_list_of_available_places(query: str) -> str:
    """Look up for doctor suggestion service available places"""
    places= get_distinct_cities_countries()
    return f"Here are the list of places where currently doctor suggestion is available, {json.dumps(places)}"