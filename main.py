import sys
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime, timedelta
import pytz
from time import sleep
import pyttsx3


"""
Script takes two arguments:
    - Departure Station
    - Target time for notification
"""
departure_station = sys.argv[1]
target_time = sys.argv[2]

#Load environmental variables for API Key
load_dotenv()
app_key = os.environ.get("app_key")

"""
Station class stores station data.
Uses StopPoint/Search endpoint to fetch station data from name.
Errors if station search name is ambiguous.
"""
class station:
    def __init__(self, name_search):
        query_base_url = 'https://api.tfl.gov.uk/StopPoint/Search/'
        query_url = f'{query_base_url}{name_search}?modes=tube&app_key={app_key}'
        
        response = response = requests.get(query_url)

        if response.status_code != 200:
            raise Exception(f"Station Search Failed Connection: Response Code {response.status_code}")
        else:
            print("Station Search Connection Successful")

        content = json.loads(response._content)
        station_list = [{"name":stop['name'], "id":stop['id']} for stop in content["matches"]]
        
        if len(station_list) == 0:
            raise Exception(f"No stations found for search: '{name_search}'")
        elif len(station_list) > 1:
            raise Exception(f"Ambiguous station name: '{name_search}'. Please enter an unambiguous station name")
        else:
            self.station_name = station_list[0]["name"]
            self.station_id = station_list[0]["id"]


"""
Arrival class stores train arrival data.
Calculates difference between current time and arrival time for 'arriving_in' variable.
"""
class arrival:
    def __init__(self, id, destination, current_location, arriving, line):
        self.id = id
        self.destination = destination
        self.current_location = current_location
        self.arriving = datetime.strptime(arriving, r'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.timezone("Europe/London"))
        self.arriving_in = (self.arriving - datetime.now(tz=pytz.timezone("Europe/London"))).total_seconds() / 60

"""
The get_arrivals function returns a list of trains departing for Wimbledon,
sorted by time to arrival
"""
def get_wim_arrivals(station_object):
    arrival_base_url = 'https://api.tfl.gov.uk/StopPoint/'
    arrival_query_string = f'{arrival_base_url}{station_object.station_id}/Arrivals'

    response = requests.get(arrival_query_string)

    if response.status_code != 200:
        raise Exception(f"Arrival Endpoint Failed Connection: Response Code {response.status_code}")
    else:
        print("Arrival Endpoint Connection Successful")

    content = json.loads(response._content)
    arrival_list = [arrival(arr['id'], 
                            arr['towards'], 
                            arr['currentLocation'], 
                            arr['expectedArrival'],
                            arr['lineName'])
                        for arr in content]

    wim_arrival_list = [train for train in arrival_list if train.destination == "Wimbledon"]
    sorted_wim_arrival_list = sorted(wim_arrival_list, key= lambda train: train.arriving)
    return sorted_wim_arrival_list

def format_notification(arrival_list_for_formatting):
    if len(arrival_list_for_formatting) > 1:
        return f"The next train to Wimbledon leaves in {arrival_list_for_formatting[0].arriving_in:.0f} minutes, and is currently {arrival_list_for_formatting[0].current_location}. The one after leaves in {arrival_list_for_formatting[1].arriving_in:.0f} minutes, and is {arrival_list_for_formatting[1].current_location}"
    elif len(arrival_list_for_formatting) == 1:
        return f"The next train to Wimbledon leaves in {arrival_list_for_formatting[0].arriving_in:.0f} minutes, and is currently {arrival_list_for_formatting[0].current_location}."
    else:
        print("No trains found")

def send_notification(arrival_list_for_testing, target_time, tested_trains):
    if len(arrival_list_for_testing) == 0:
        return ""
    elif arrival_list_for_testing[0].arriving_in <= float(target_time) and arrival_list_for_testing[0].id not in set(tested_trains):
        tested_trains.append(arrival_list_for_testing[0].id)
        notification = format_notification(arrival_list_for_testing)
        return notification
    else:
        print("No notification required")
        return ""

def speak(engine, notification):
    engine.say(notification)
    print("Spoken")
    engine.runAndWait()

def main(station_argument, target_time):
    chosen_station = station(station_argument)
    tested_trains = []
    engine = pyttsx3.init()
    engine.setProperty('volume',5.0)
    engine.setProperty('rate', 175)
    speak(engine, "WombleBot Active")

    while True:
        main_arrival_list = get_wim_arrivals(chosen_station)
        main_notification = send_notification(main_arrival_list, target_time, tested_trains)
        if main_notification == "":
            pass
        else:
            speak(engine, main_notification)
        sleep(30)

    
if __name__ == "__main__":
    main(departure_station, target_time)