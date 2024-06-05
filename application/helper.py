import geoip2.database
import requests
from dotenv import dotenv_values
from flask import current_app
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAI, ChatOpenAI

from application.models.doctor_n_others import Chamber

GOOGLE_API_KEY = dotenv_values(".env").get("GOOGLE_API_KEY", "AIzaSyDh5EIjypY-vJpzbhHge6P4kHy_kwAESPs")


def is_subscriptable(obj):
    return hasattr(obj, '__getitem__')


def get_distinct_cities_countries():
    try:
        query_res = Chamber.query.with_entities(Chamber.city, Chamber.country).distinct().all()
        for entry in query_res:
            city, country = entry
            print(city, country)
        return [f"{city}, {country}" for city, country in query_res if city is not None]
    except Exception as e:
        print(str(e))
        return []

def get_lat_long_from_google_maps(location) -> dict:
    """Get latitude and longitude from google maps.
    Args:
        location (str): Location name
    Returns:
        dict: Latitude and longitude
        
        Example: {"lat": 23.8103, "lng": 90.4125}
    """
    latlong = {}  
    try:
        geo_location = requests.get(
            f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={GOOGLE_API_KEY}").json()
        if geo_location['status'] == "OK":
            first_address = geo_location.get('results', [None])[0]
            if first_address:
                lat = first_address['geometry']['location']['lat']
                lng = first_address['geometry']['location']['lng']
                latlong = {"lat": lat, "lng": lng}
    except Exception as e:
        print(str(e))
    return latlong 

def get_location_from_google_maps(lat, lang) -> dict:
    address = {
        "city": "", "country": "", "formatted": ""
    }
    try:
        geo_location = requests.get(
            f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lang}&key={GOOGLE_API_KEY}").json()
        if geo_location['status'] == "OK":
            first_address = geo_location['results'][0] if 'results' in geo_location else None
            if first_address:
                print(first_address)
                for component in first_address['address_components']:
                    current_app.logger.info(f"---------------------------- {component}")
                    if "plus_code" not in component['types'] and "route" not in component['types'] and "street_number" not in component['types']:
                        address['formatted'] += f"{component['long_name']}, "

                    if "sublocality" in component['types']:
                        address['area'] = component['long_name']
                    elif "administrative_area_level_2" in component['types']:
                        address['city'] = component['long_name']
                    elif "country" in component['types']:
                        address['country'] = component['long_name']

                address['formatted'] = address['formatted'][:-2] if len(address['formatted']) > 0 else ""
        print('---address', address)

        return address
    except Exception as e:
        print(str(e))
    finally:
        return address


def get_location_from_ip(ip) -> dict:
    import geocoder
    geo_location = geocoder.ip(ip)
    return {
        "points": geo_location.latlng,
        "city": geo_location.city,
        "country": geo_location.country,
        "formatted":f"{geo_location.city}, {geo_location.country}"
    }
    # with geoip2.database.Reader('GeoLite2/GeoLite2-City.mmdb') as client:
    #     response = client.city(ip)
    #     user_location = {
    #         "points": (response.location.latitude, response.location.longitude),
    #         "city": response.city.name,
    #         "sub_division": response.subdivisions.most_specific.name,
    #         "country": response.country.name
    #     }
    #     return user_location


def get_location_from_lat_lng(lat, lng):
    try:
        OPENAI_API_KEY = dotenv_values(".env").get("OPENAI_API_KEY")
        prompt = ChatPromptTemplate.from_template(
            "Tell me a city, country from this point ({lng},{lat}). "
            "You must only return the city name and country name such as Dhaka, Bangladesh."
        )
        output_parser = StrOutputParser()
        model = ChatOpenAI(
            model="gpt-4-0125-preview",
            streaming=False,
            max_tokens=1000,
            temperature=0.0,
            openai_api_key=OPENAI_API_KEY, )
        chain = (prompt | model | output_parser)
        location = chain.invoke({"lng": lng, "lat": lat})
        return location
    except Exception as e:
        return None


if __name__ == "__main__":
    get_distinct_cities_countries()
