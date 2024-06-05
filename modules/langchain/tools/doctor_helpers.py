import json
from sqlalchemy.sql import text
from database.service import db
from flask import current_app


def format_doctor_data(doctors_raw, language):
    structured_docs = []
    # unique_sources = set()

    for doctor in doctors_raw:
        # Assuming doctor.chamber_created_at and doctor.chamber_deleted_at are datetime objects or None
        structured_doc = {
            "doctor_id": doctor.doctor_id,
            "lat": doctor.lat,
            "long": doctor.long,
            "address": doctor.address,
            "contact_for_appointment": doctor.contact_no,
            "created_at": (
                doctor.chamber_created_at.isoformat()
                if doctor.chamber_created_at
                else None
            ),
            "deleted_at": (
                doctor.chamber_deleted_at.isoformat()
                if doctor.chamber_deleted_at
                else None
            ),
            "specializations": doctor.specializations,
            "experiences": doctor.experiences
            or "",  # Simplify if-check for None or empty string
            "qualifications": doctor.qualifications or "",
            "description": doctor.doctor_description,
            "user_id": doctor.user_id,
            "first_name": doctor.first_name,
            "last_name": doctor.last_name,
            "distance_from_patient_in_m": doctor.distance,
            "distance_from_patient_in_km": (
                f"প্রায় {round(doctor.distance / 1000, 2)} কিমি"
                if language == "Bangla"
                else f"Approx. {round(doctor.distance / 1000, 2)} km"
            ),
            "source_of_reference": doctor.source_of_reference,
        }
        structured_docs.append(structured_doc)
        # unique_sources.add(doctor.source_of_reference)

    # Sort by distance after structuring docs to keep the operation outside the loop
    sorted_docs = sorted(structured_docs, key=lambda x: x["distance_from_patient_in_m"])

    return sorted_docs


def search_doctors_by_proximity(
    user_lat, user_long, language, specialization_search_terms={}
):
    """Searches for nearby doctors, optionally filtering by specialization, qualifications, and description."""
    search_radii = [4000, 6000, 10000]
    regex_conditions = []
    parameters = {
        "user_lat": user_lat,
        "user_lon": user_long,
        "search_string": " ".join(
            specialization_search_terms.get("regex_search_items_as_a_world", [])
            + specialization_search_terms.get("regex_search_items_as_prefix", [])
        ),
    }
    for idx, term in enumerate(
        specialization_search_terms.get("regex_search_items_as_a_world", [])
    ):
        """
        for mysql regex search
        """
        if " " not in term:
            regex_key = f"regex_term_i{idx}"
            regex_conditions.append(
                f"( LOWER(doctors.specializations) REGEXP :{regex_key} OR LOWER(doctors.description) REGEXP :{regex_key} OR LOWER(doctors.qualifications) REGEXP :{regex_key})"
            )
            parameters[regex_key] = f"\\b{term.lower()}\\b"

    for idx, term in enumerate(
        specialization_search_terms.get("regex_search_items_as_prefix", [])
    ):
        """
        for mysql regex search
        """
        if " " not in term:
            regex_key = f"regex_term_j{idx}"
            regex_conditions.append(
                f"( LOWER(doctors.specializations) REGEXP :{regex_key} OR LOWER(doctors.description) REGEXP :{regex_key} OR LOWER(doctors.qualifications) REGEXP :{regex_key})"
            )
            parameters[regex_key] = f"\\b{term.lower()}.*"

    # Combine all conditions
    combined_conditions = " OR ".join(regex_conditions) if regex_conditions else "1=1"
    print("cm", combined_conditions)
    for radius in search_radii:
        parameters["radius"] = radius
        query_text = f"""
            SELECT
                doctor_chambers.id AS chamber_id, 
                doctor_chambers.lat, 
                doctor_chambers.`long`, 
                doctor_chambers.address, 
                doctor_chambers.contact_no,
                doctor_chambers.created_at AS chamber_created_at, 
                doctor_chambers.deleted_at AS chamber_deleted_at, 
                doctor_chambers.source_of_reference,
                doctors.id AS doctor_id, 
                doctors.user_id, 
                doctors.specializations, 
                doctors.experiences, 
                doctors.qualifications, 
                doctors.description AS doctor_description,
                users.first_name, users.last_name,
                ST_Distance_Sphere(POINT(doctor_chambers.`long`, doctor_chambers.lat), POINT(:user_lon, :user_lat)) AS distance,
                MATCH(doctors.specializations, doctors.qualifications, doctors.keywords, doctors.description) AGAINST(:search_string IN NATURAL LANGUAGE MODE) AS relevance
            FROM doctor_chambers
            INNER JOIN doctors ON doctors.id = doctor_chambers.doctor_id
            INNER JOIN users ON doctors.user_id = users.id
            WHERE ST_Distance_Sphere(POINT(doctor_chambers.`long`, doctor_chambers.lat), POINT(:user_lon, :user_lat)) <= :radius
            AND ({combined_conditions})
            ORDER BY relevance DESC, distance ASC
            LIMIT 4
            """
        current_app.logger.info("SQL Query from tool:", query_text)
        current_app.logger.info("Parameters from tool:", parameters)

        doctors_found = db.session.execute(text(query_text), parameters).fetchall()
        if doctors_found:
            break
    if doctors_found:
        sorted_docs = format_doctor_data(doctors_found, language)

        if sorted_docs:
            base_response = (
                "এখানে কিছু নিকটস্থ চিকিৎসকের তালিকা রয়েছে। আপনার পছন্দ শেয়ার করুন যাতে আমি আপনাকে ম্যাপে চিকিৎসকের চেম্বারের ডাইরেকশন দেখাতে পারি। আপনি কাকে দেখাতে আগ্রহী?\n"
                if language == "Bangla"
                else "Here is a list of nearby doctors. Please share your preference so that I can provide you with directions to the doctor's chamber. Which one would you prefer to consult?\n"
            )
            base_response_with_iterative_html = (
                """<br/><div className="cardContainer">"""
            )
            for doctor in sorted_docs:
                source_info = (
                    f"সূত্র: {doctor['source_of_reference']}"
                    if language == "Bangla"
                    else f"Source: {doctor['source_of_reference']}"
                )
                base_response_with_iterative_html += f"""<div className="cardColumn">
                    <div className="profileCard">
                        <div className="profileHeader text-cut-1">{doctor['first_name']} {doctor['last_name']}
                        <span className="infoIcon" title="{source_info}">&#9432;</span>
                        </div>
                        <div className="profileBody">
                            <h5 className="profileTitle">
                                <span className="text-cut-1">{doctor['qualifications']}</span>
                                <span className="text-cut-1">{doctor['specializations']}</span>
                            </h5>
                            <p className="profileLocation">
                                <span className="text-cut-1">{doctor['address']}</span>
                                <span className="text-cut-1">{doctor['contact_for_appointment']}</span>
                            </p>
                            <p className="profileText">
                                <span className="text-cut-1">{doctor['distance_from_patient_in_km']}</span>
                            </p>
                            <input type="hidden" name="lat" value="{doctor['lat']}"/>
                            <input type="hidden" name="long" value="{doctor['long']}"/>
                        </div>
                    </div>
                </div>"""

            base_response_with_iterative_html += """</div>"""

            return base_response + base_response_with_iterative_html
    else:
        return (
            "বর্তমানে আপনার অবস্থানের ভিত্তিতে, আপনার নির্দিষ্ট সমস্যা অনুযায়ী আমাদের ইকোসিস্টেমে কোনও ডাক্তার উপলব্ধ নেই"
            if language == "Bangla"
            else "Currently, there are no doctors available in our ecosystem near user's location based on the specified concern"
        )


if __name__ == "__main__":
    search_doctors_by_proximity(
        user_lat=23.822216,
        user_long=90.433733,
        specialization_search_terms=["urology", "cardiology"],
    )
