from flask import Flask, render_template, request
import json
import os
import openai
import googlemaps
from urllib.parse import quote_plus

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

openai.api_key = os.environ.get("OPENAI_KEY")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')

SYSTEM_ROLE = """You are tasked to create a list of points of interest according to the user's instructions.
As a title, use the last known official name of the place or building. I will need it to find this place using Google Places API. If a place doesn't have a well-known name, add an address (street name and street number if available) to the title.
If "type of points of interest" instructions are unclear, make a list of most popular attractions in this area.
In your answer, do not include any text and only provide the location list in the following format: 
[{"general_location": "<city or general area and country>", "title": <building name or address>, "info": <information about the building>}, {"general_location": "<city or general area and country>", "title": <building name or address>, "info": <information about the building>}]"""


@app.route('/', methods=["GET", "POST"])
def show_homepage():
    if request.method == "GET":
        return render_template("index.html")
    if request.method == "POST":
        city = request.form['City']
        interest = request.form['Type']
        number = request.form['Number']

        # print(city, interest, number)

        completion = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": f"Location: {city}\n"
                                            f"Number of points of interest: {number}\n"
                                            f"Type of points of interest: {interest}"}
            ],
            temperature=0,
            max_tokens=1024,
            frequency_penalty=0,
            presence_penalty=0,
        )

        print(f"Location: {city}\n"
              f"Number of points of interest: {number}\n"
              f"Type of points of interest: {interest}\n")
        print(completion["choices"][0]["message"]["content"])

        locations = completion["choices"][0]["message"]["content"]
        locations_json = json.loads(locations)

        map_locations = []

        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

        for location in locations_json:
            # Geocode the location
            place_data = location['title'] + ', ' + location['general_location']
            result = gmaps.find_place(input=place_data,
                                      input_type="textquery",
                                      fields=['formatted_address', "place_id", "geometry"])

            if result["status"] == "OK":
                formatted_address = result["candidates"][0]['formatted_address']
                latlng = result["candidates"][0]['geometry']['location']
                place_id = result["candidates"][0]['place_id']
                maps_link = f"https://www.google.com/maps/search/?api=1&query={quote_plus(formatted_address)}&query_place_id={quote_plus(place_id)}"

                map_locations.append({
                    'title': location["title"],
                    'info': location['info'],
                    'address': formatted_address,
                    'latlng': latlng,
                    'maps_link': maps_link
                })
            else:
                non_found_address = location["general_location"]

                result = gmaps.find_place(input=non_found_address,
                                          input_type="textquery",
                                          fields=['formatted_address', "place_id", "geometry"])

                formatted_address = result["candidates"][0]['formatted_address']
                latlng = result["candidates"][0]['geometry']['location']
                place_id = result["candidates"][0]['place_id']
                maps_link = f"https://www.google.com/maps/search/?api=1&query={quote_plus(formatted_address)}&query_place_id={quote_plus(place_id)}"

                map_locations.append({
                    'title': location["title"],
                    'info': location['info'],
                    'address': formatted_address,
                    'latlng': latlng,
                    'maps_link': maps_link
                })

        map_locations_json = json.dumps(map_locations)
        return render_template("map.html", map_locations_json=map_locations_json, map_locations=map_locations)


@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Server Error: {error}")
    print(f"Server Error: {error}")
    return "Oh no! You encountered an internal server error.\n" \
           "Sorry about that. We will review the logs and fix it soon.\n" \
           "In the meantime, give it another try!\n" \
           "https://naivigator.app/", 500


if __name__ == "__main__":
    app.run(debug=True, port=5001, host="127.0.0.1")
