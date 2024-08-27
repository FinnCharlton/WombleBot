"""
Import Modules
"""
import sys
from dotenv import load_dotenv
import os
import logging
import requests
import json
from datetime import datetime, timedelta
import pytz
from time import sleep
import pyttsx3
import subprocess


"""
Initialise Logging
"""
#Logging to file
logging.basicConfig(level=logging.DEBUG,
                    format = "%(asctime)s %(name)-25s %(levelname)-10s %(message)s",
                    datefmt="%d-%m %H:%M:%S",
                    filename="womble.log",
                    filemode="a"
                    )

#Create and add console logging handler
console_logging = logging.StreamHandler()
console_logging.setLevel(logging.INFO)
console_format = logging.Formatter("%(name)-12s %(levelname)-8s %(message)s")
console_logging.setFormatter(console_format)
logging.getLogger("").addHandler(console_logging)


"""
Script takes two arguments:
    - Departure Station
    - Target time for notification
"""
departure_station = sys.argv[1]
target_time = sys.argv[2]
logging.debug("Arguments Loaded")


"""
Load environmental variables for API Keys
"""
load_dotenv()
app_key = os.environ.get("app_key")
# voice_key = os.environ.get("voice_key")
logging.debug("Environmental Variables Loaded")


"""
Station class stores station data.
Uses StopPoint/Search endpoint to fetch station data from name.
Errors if station search name is ambiguous, or if no stations are found.
"""
class station:

    #Init forms query for searching the StopPoint/Search endpoint. This is used to retrieve the ID of the specified station
    def __init__(self, name_search):
        query_base_url = 'https://api.tfl.gov.uk/StopPoint/Search/'
        query_url = f'{query_base_url}{name_search}?modes=tube&app_key={app_key}'
        
        #Get response
        response = response = requests.get(query_url)

        #Check response status code - raise exception if not 200
        if response.status_code != 200:
            logging.error(f"Station Search Failed Connection: Response Code {response.status_code}")
            raise Exception
        else:
            logging.info("Station Search Connection Successful")

        #Search endpoint can return multiple stations. Returned stations are parsed into list of dicts
        content = json.loads(response._content)
        station_list = [{"name":stop['name'], "id":stop['id']} for stop in content["matches"]]
        logging.debug("Station Content Retrieved")
        
        #Raise Exception if 0 or multiple stations are returned. Only one station should be returned from the user search. Else set instance variables to station data
        if len(station_list) == 0:
            logging.error(f"No stations found for search: '{name_search}'")
            raise Exception
        elif len(station_list) > 1:
            logging.error(f"Ambiguous station name: '{name_search}'. Please enter an unambiguous station name")
            raise Exception
        else:
            self.station_name = station_list[0]["name"]
            self.station_id = station_list[0]["id"]
            logging.info("Station Information Set")


"""
Arrival class stores train arrival data.
Calculates difference between current time and arrival time for 'arriving_in' variable.
"""
class arrival:
    def __init__(self, id, destination, current_location, arriving, line):
        self.id = id
        self.destination = destination
        self.current_location = current_location

        #Parse arrival time into datetime type, assuring London timezone. Calculate arrival interval, again ensuring correct timezone
        self.arriving = datetime.strptime(arriving, r'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.timezone("Europe/London"))
        self.arriving_in = (self.arriving - datetime.now(tz=pytz.timezone("Europe/London"))).total_seconds() / 60


"""
The get_arrivals function returns a list of trains departing for Wimbledon,
sorted by time to arrival
"""
def get_wim_arrivals(station_object):

    #Define arrivals search query
    arrival_base_url = 'https://api.tfl.gov.uk/StopPoint/'
    arrival_query_string = f'{arrival_base_url}{station_object.station_id}/Arrivals'

    #Get response
    response = requests.get(arrival_query_string)

    #Check response status code - raise exception if not 200
    if response.status_code != 200:
        logging.error(f"Arrival Endpoint Failed Connection: Response Code {response.status_code}")
        raise Exception
    else:
        logging.info("Arrival Endpoint Connection Successful")

    #Parse returned arrivals content. Data is parsed as a list of arrival class instances
    content = json.loads(response._content)
    arrival_list = [arrival(arr['id'], 
                            arr['towards'], 
                            arr['currentLocation'], 
                            arr['expectedArrival'],
                            arr['lineName'])
                        for arr in content]
    logging.info("Arrival Information Set")

    #Filter arrivals list to only those heading to Wimbledon
    wim_arrival_list = [train for train in arrival_list if train.destination == "Wimbledon"]

    #Sort arrivals list by arrival time
    sorted_wim_arrival_list = sorted(wim_arrival_list, key= lambda train: train.arriving)

    return sorted_wim_arrival_list


"""
The format_notifications function returns the notification content to be played by the text-to-speech converter.
It takes a sorted list of depatures, assuming the first item is the first train to arrive.
"""
def format_notification(arrival_list_for_formatting):

    #If there are multiple Wimbledon trains returned, the notification displays the first two trains
    if len(arrival_list_for_formatting) > 1:
        logging.info(">1 Trains Found")
        return f"The next train to Wimbledon leaves in {arrival_list_for_formatting[0].arriving_in:.0f} minutes, and is currently {arrival_list_for_formatting[0].current_location}. The one after leaves in {arrival_list_for_formatting[1].arriving_in:.0f} minutes, and is {arrival_list_for_formatting[1].current_location}"
    
    #If only one train is found, it is the only one displayed
    elif len(arrival_list_for_formatting) == 1:
        logging.info("1 Train Found")
        return f"The next train to Wimbledon leaves in {arrival_list_for_formatting[0].arriving_in:.0f} minutes, and is currently {arrival_list_for_formatting[0].current_location}."
    
    else:
        logging.info("No trains found")


"""
The send_notification function returns a notification only if it should be displayed.
As input it takes the sorted arrivals list, the target time entered by the user, and a list of arrival ids.
It returns the notification if the first train is arriving in less minutes than the target time, and if the train has not been notified on before (i.e. not in the list of tested trains)
"""
def send_notification(arrival_list_for_testing, target_time, tested_trains):

    #If there are no trains in list, return a blank string
    if len(arrival_list_for_testing) == 0:
        return ""
    
    #If the correct conditions are met, add the arrival id of the first train to the tested_trains list and call format_notification to return a notification for dispaly
    elif arrival_list_for_testing[0].arriving_in <= float(target_time) and arrival_list_for_testing[0].id not in set(tested_trains):

        tested_trains.append(arrival_list_for_testing[0].id)
        notification = format_notification(arrival_list_for_testing)

        logging.info("Notification Required")
        return notification
    

    else:
        logging.info("No notification required")
        return ""


"""
The speak function plays an input notification with the supplied text-to-speech engine
"""

def speak(engine, notification):
    engine.say(notification)
    logging.debug(f"Spoke: {notification}")
    engine.runAndWait()


"""
Main Function. Take the two system arguments as inputs.
"""
def main(station_argument, target_time):

    #Initialise station class with user input
    chosen_station = station(station_argument)

    #Initialise empty tested_trains list
    tested_trains = []

    #Initialise Text-To-Speech Engine, and set volume and rate properties
    engine = pyttsx3.init()
    engine.setProperty('volume',20.0)
    engine.setProperty('rate', 175)
    logging.debug("Text-to-Speech Engine initialised")

    #Initialise intial conditions for loop
    run_counter = 0
    target_runs = 120

    #Play Activation Message to show initialisation has been successful
    speak(engine, "WombleBot Active")

    #Loop until the target number of runs have been completed
    while run_counter < target_runs:

        logging.info(f"Beginning Run {run_counter}")

        #Use above functions to fetch sorted arrival list and notification, if required
        main_arrival_list = get_wim_arrivals(chosen_station)
        main_notification = send_notification(main_arrival_list, target_time, tested_trains)

        #Play notification 
        if main_notification == "":
            pass
        else:
            speak(engine, main_notification)

        #Wait 30 seconds and increment run counter
        sleep(30)
        run_counter += 1


if __name__ == "__main__":
    main(departure_station, target_time)
    logging.debug("All runs completed")