"""
Another file for more ideas and how to implement some of the things that can be appllied

So here again i will do Travel Accomendation
The goal is to have an iternary of the travel 
    1. FlightInfo
    2. WeatherInfo
    3. SafetyInfo
    


"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import anthropic
import os
import logging
from dotenv import load_dotenv
import requests
import json




# Set up logging configuration
logging.basicConfig(
    level = logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# this load the .env
load_dotenv()


client = anthropic.Anthropic()



# Real data sources (no LLM involved)
def get_weather(latitude, longitude):
    """Real current temperature from Open-Meteo."""
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m"
    )
    data = response.json()
    return data["current"]["temperature_2m"]
 
 
def search_kb():
    """Load the whole knowledge base from the JSON file."""
    with open("kb.json", "r") as f:
        return json.load(f)
 
 
def find_kb_entry(city: str):
    """Find a matching destination entry in the knowledge base by city name."""
    kb_data = search_kb()
    return next(
        (d for d in kb_data["destinations"] if city.lower() in d["destination"].lower()),
        None,
    )
 









# Step 1: Define the data models for each stage

class FlightInfo(BaseModel):
    """First LLM call: Extract basic event information of FlightInfo"""
    description: str = Field(description="Information of the flight. What date/time is the flight, duration of the flight, and the airline the flight is on.")
    is_calendar_event: bool = Field(
        description="Whether this text describes a calendar event."
    )
    confidence_score: float = Field(description="Confidence score between 0 and 1")


class WeatherInfo(BaseModel):
    """Second LLM call: Extract the weather information of the destination"""
    description: str = Field(description="Information of the destination's weather and its forcasts for the next few days")
    confidence_score: float = Field(description="Confidence score between 0 and 1")


class SafetyInfo(BaseModel):
    """Third LLM call: extract the safety measures of a countries based on its criminal rates towards tourists"""
    description: str = Field(description="Information of the criminality in that country and its safetyness for tourist")
    confidence_score: float = Field(description="Confidence score between 0 and 1")


class ItineraryInfo(BaseModel):
    """Fourth LLM call: generate a day-by-day itinerary"""
    itinerary: list[str] = Field(description="Day-by-day plan, one bullet per day")
 
 
class DestinationCoordinates(BaseModel):
    """Extract destination city + coordinates so we can call real APIs/KB lookups"""
    city: str
    latitude: float
    longitude: float





# ---------------------------------------------------------------------------------------
# step 2: defining the functions
def extract_event_info(user_input: str) -> FlightInfo:
    """First LLM call to determine if input is a calendar event"""
    logger.info("Starting event extraction analysis")
    logger.debug(f"Input text: {user_input}")

    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B, %d, %Y')}"

    response = client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"{date_context}. {user_input}\n\n"
                f"Only include details that are explicitly stated or clearly implied in the text above. "
                f"If something (like the airline) isn't mentioned, say 'not specified' rather than guessing.",
            }
        ],
        output_format=FlightInfo,
    )
    flightinformation = response.parsed_output
    return flightinformation



def extract_weather_info(user_input: str, coords: DestinationCoordinates) -> WeatherInfo:
    """Get REAL current temperature, then have Claude phrase a helpful summary"""
    logger.info("Starting weather extraction analysis")

    real_temp = get_weather(coords.latitude, coords.longitude)
    logger.info(f"Real temperature for {coords.city}: {real_temp}°C")

    response = client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"The current real temperature in {coords.city} is {real_temp}°C. "
                            f"In 1-2 short sentences, write a helpful weather summary for a traveler, "
                            f"including general seasonal context for this trip: {user_input}",
            }
        ],
        output_format=WeatherInfo,
    )
    weatherinformation = response.parsed_output
    return weatherinformation




def extract_safety_info(user_input: str, coords: DestinationCoordinates) -> SafetyInfo:
    """Get safety info — from the real knowledge base if available, otherwise from the model's general knowledge"""
    logger.info("Starting safety info analysis")
 
    kb_entry = find_kb_entry(coords.city)
 
    if kb_entry:
        logger.info(f"Found KB entry for {coords.city}")
        response = client.messages.parse(
            model="claude-sonnet-5",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": f"Based on this real safety data: {kb_entry['safety_notes']} — "
                                f"write a 1-2 sentence helpful safety summary for a traveler on this trip: {user_input}",
                }
            ],
            output_format=SafetyInfo,
        )
    else:
        logger.info(f"No KB entry found for {coords.city}, falling back to general knowledge")
        today = datetime.now()
        date_context = f"Today is {today.strftime('%A, %B %d, %Y')}"
        response = client.messages.parse(
            model="claude-sonnet-5",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": f"{date_context}. Based on this trip: {user_input} — in 1-2 short sentences, "
                                f"what is the general safety situation for tourists at the destination, including common risks or scams?",
                }
            ],
            output_format=SafetyInfo,
        )
 
    return response.parsed_output
 




def extract_itinerary(user_input: str) -> list[str]:
    """Generate a day-by-day itinerary"""
    logger.info("Starting itinerary generation")
    logger.debug(f"Input text: {user_input}")
 
    today = datetime.now()
    date_context = f"Today is {today.strftime('%A, %B %d, %Y')}"
 
    response = client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=1536,
        messages=[
            {
                "role": "user",
                "content": f"{date_context}. Based on this trip: {user_input} — write a day-by-day itinerary, "
                            f"one short bullet per day. If the trip is longer than 14 days, group it into weekly "
                            f"themes instead of every single day.",
            }
        ],
        output_format=ItineraryInfo,
    )
    itineraryinformation = response.parsed_output
    return itineraryinformation.itinerary





# ---------------------------------------------------------------------------
 


def extract_coordinates(user_input: str) -> DestinationCoordinates:
    """Extract destination city + coordinates so we can call the real weather API"""
    response = client.messages.parse(
        model="claude-sonnet-5",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"Extract the main destination city and its approximate latitude/longitude from this trip: {user_input}",
            }
        ],
        output_format=DestinationCoordinates,
    )
    return response.parsed_output



# ---------------------------------------------------------------------------

class TravelSummary(BaseModel):
    """Combined result of all three checks"""
    flight_info: str
    flight_confidence: float
    weather_info: str
    safety_info: str
    itinerary: list[str] = Field(description="Day-by-day plan, one bullet per day")


def process_calendar_request(user_input: str) -> Optional[TravelSummary]:
    """Main function implementing the prompt chain with date check"""
    logger.info("Processing calendar request")
    logger.debug(f"Raw input: {user_input}")

    # First LLM call: Extract basic info
    initial_extraction = extract_event_info(user_input)

    # Gate Check: Verify if it is a calendar event with sufficient confidence
    if (
        not initial_extraction.is_calendar_event
        or initial_extraction.confidence_score < 0.6
    ):
        logger.warning(
            f"Gate check failed - is_calendar_event: {initial_extraction.is_calendar_event}, confidence {initial_extraction.confidence_score}"
        )
        return None

    logger.info("Gate check passed, proceeding with event processing")

    # Extract destination coordinates ONCE, reused by both weather and safety
    coords = extract_coordinates(user_input)

    weather_details = extract_weather_info(user_input, coords)
    logger.info(f"Weather info: {weather_details.description}")

    safety_details = extract_safety_info(user_input, coords)
    logger.info(f"Safety info: {safety_details.description}")

    # Fourth LLM call: Itinerary
    itinerary = extract_itinerary(user_input)
    logger.info(f"Itinerary: {itinerary}")

    return TravelSummary(
        flight_info=initial_extraction.description,
        flight_confidence=initial_extraction.confidence_score,
        weather_info=weather_details.description,
        safety_info=safety_details.description,
        itinerary=itinerary,
    )





# ---------------------------------------------------------------------------
# Test the chain with a valid input
 
if __name__ == "__main__":
    user_input = "I am flying next week from now to Central Asia, I will begin and end in Russia  for a month, i'd like to visit kazahstan as well, and I am going with an American Airline"
 
    result = process_calendar_request(user_input)
    if result:
        print()
        print(f"Confidence: {result.flight_confidence}")
        print()
        print(f"Flight info: {result.flight_info}")
        print()
        print(f"Weather info: {result.weather_info}")
        print()
        print(f"Safety info: {result.safety_info}")
        print()
        print("Itinerary:")
        for day in result.itinerary:
            print(f"  - {day}")
    else:
        print("Request did not pass the gate check.")