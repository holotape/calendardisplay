from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU
import datetime
import time
import os
from icalendar import Calendar
import pytz
import requests

from waveshare_epd import epd2in13_V3
from PIL import Image, ImageDraw, ImageFont
from dateutil.rrule import rrule
from dateutil.parser import parse
from dateutil.rrule import rrule, YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY, SECONDLY

RRULE_FREQ_MAP = {
    'YEARLY': YEARLY,
    'MONTHLY': MONTHLY,
    'WEEKLY': WEEKLY,
    'DAILY': DAILY,
    'HOURLY': HOURLY,
    'MINUTELY': MINUTELY,
    'SECONDLY': SECONDLY
}

WEEKDAY_MAP = {
    "MO": MO,
    "TU": TU,
    "WE": WE,
    "TH": TH,
    "FR": FR,
    "SA": SA,
    "SU": SU
}

WEEKDAY_ORDINAL_MAP = {
    "1MO": MO(1),
    "2MO": MO(2),
    "3MO": MO(3),
    "4MO": MO(4),
    "-1MO": MO(-1),

    "1TU": TU(1),
    "2TU": TU(2),
    "3TU": TU(3),
    "4TU": TU(4),
    "-1TU": TU(-1),

    "1WE": WE(1),
    "2WE": WE(2),
    "3WE": WE(3),
    "4WE": WE(4),
    "-1WE": WE(-1),

    "1TH": TH(1),
    "2TH": TH(2),
    "3TH": TH(3),
    "4TH": TH(4),
    "-1TH": TH(-1),

    "1FR": FR(1),
    "2FR": FR(2),
    "3FR": FR(3),
    "4FR": FR(4),
    "-1FR": FR(-1),

    "1SA": SA(1),
    "2SA": SA(2),
    "3SA": SA(3),
    "4SA": SA(4),
    "-1SA": SA(-1),

    "1SU": SU(1),
    "2SU": SU(2),
    "3SU": SU(3),
    "4SU": SU(4),
    "-1SU": SU(-1),
}

def get_next_event(file_path):
    local_tz = pytz.timezone("America/Toronto")
    utc_tz = pytz.timezone("UTC")
    now = datetime.datetime.now(local_tz) # .replace(tzinfo=None)
    #dtstart_for_rrule = datetime.datetime.fromtimestamp(dtstart)
    #recurrences = list(rrule(dtstart=dtstart_for_rrule, **rrule_params))

    # Check if the input is a URL or a local file path
    if file_path.startswith("http://") or file_path.startswith("https://"):
        headers = {"Cache-Control": "no-cache"} # Don't cache the ICS file
        response = requests.get(file_path)
        response.raise_for_status()  # raise an exception if there was an error fetching the URL
        cal_content = response.content
    else:
        with open(file_path, "rb") as f:
            cal_content = f.read()

    cal = Calendar.from_ical(cal_content)

    # for debugging purposes only
    for event in cal.walk("VEVENT"):
        print(event.get("summary"), event.get("dtstart").dt)
        break

    # logic
    next_event = None
    min_diff = float("inf")

    for event in cal.walk("VEVENT"):
        event_start_dt = event.get("dtstart").dt
        rrule_val = event.get('rrule')

        if rrule_val:
            # Adjust the DTSTART for rrule
            if isinstance(event_start_dt, datetime.datetime):
                dtstart_for_rrule = event_start_dt.astimezone(utc_tz)
            else:
                dtstart_for_rrule = event_start_dt  # For date objects, no conversion is needed

            rrule_params = {k.lower(): v for k, v in rrule_val.items()}
            
            if 'freq' in rrule_params:
                rrule_params['freq'] = RRULE_FREQ_MAP[rrule_params['freq'][0]]
            
            if 'byweekday' not in rrule_params:
                rrule_params['byweekday'] = None
            if 'byday' in rrule_params:
                days = rrule_params['byday']
                if isinstance(rrule_params['byweekday'], list):
                    rrule_params['byweekday'] = rrule_params['byweekday'][0]
                if isinstance(rrule_params['wkst'], list):
                    rrule_params['wkst'] = rrule_params['wkst'][0]
                del rrule_params['byday']

            # Extract single datetime object for UNTIL if present
            if 'until' in rrule_params:
                rrule_params['until'] = rrule_params['until'][0]

            # Handle WKST if present
            if 'wkst' in rrule_params:
                wkst_str = rrule_params['wkst'][0]  # Get the string representation
                if wkst_str in WEEKDAY_MAP:
                    rrule_params['wkst'] = WEEKDAY_MAP[wkst_str]
                else:
                    rrule_params['wkst'] = int(wkst_str)
                
            # Create the rrule
            recurrences = list(rrule(dtstart=dtstart_for_rrule, **rrule_params))

            # Print for debugging
            print("Recurrences:", recurrences)

            for recur in recurrences:
                # Modify logic to check if recurring event is the next event
                if recur > now:
                    diff = (recur - now).total_seconds()
                    if 0 <= diff < min_diff:
                        min_diff = diff
                        next_event = {
                            "summary": event.get("summary"),
                            "start": recur,
                            "end": recur + (event.get("dtend").dt.replace(tzinfo=None) - event_start_dt.replace(tzinfo=None)),
                            "location": event.get("location"),
                        }

    return next_event

def wrap_text(text, font, max_width):
    lines = []
    words = text.split()
    
    while words:
        line = ''
        while words and font.getsize(line + words[0])[0] <= max_width:
            line += (words.pop(0) + ' ')
        lines.append(line)

    return lines

def draw_event_details(draw, event, max_width):
    # Put the path to you font of choice below
    font = ImageFont.truetype("/usr/share/fonts/truetype/chicago/Chicago Normal.ttf", 20)
    summary_lines = wrap_text(event['summary'], font, max_width)

    # Prepare event details
    # summary = event['summary']
    start_time = f"Start: {event['start'].strftime('%Y-%m-%d %H:%M')}"
    end_time = f"End: {event['end'].strftime('%Y-%m-%d %H:%M')}"
    location = event['location']

    y_offset = 0
    for line in summary_lines:
        draw.text((0, y_offset), line, font=font, fill=0)
        y_offset += font.getsize(line)[1]

    draw.text((0, y_offset), start_time, font=font, fill=0)
    y_offset += font.getsize(start_time)[1]

    draw.text((0, y_offset), end_time, font=font, fill=0)
    y_offset += font.getsize(end_time)[1]

    draw.text((0, y_offset), location, font=font, fill=0)

FLIP_DISPLAY = True # Set this to False if you'd like to flip the display rightside-up

def display_next_event(epd, event, full_update=False):
            
    # create the image buffer
    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    draw_event_details(draw, event, epd.height)

    # Rotate the image if FLIP_DISPLAY is set to True
    if FLIP_DISPLAY:
        image = image.rotate(180)

    # display the image buffer
    epd.display(epd.getbuffer(image))

    # put the display to sleep
    epd.sleep()

def read_ics_link():
    with open("ics_link.txt", "r") as f:
        return f.readline().strip()

MAX_SLEEP_DURATION = 60 # In seconds, 300 is 5 mins, 600 is 10, 900 is 15

if __name__ == "__main__":
    epd = epd2in13_V3.EPD()
    epd.init()
    
    # !!!!! Be sure to open up ics_link_sample.txt and follow the instructions
    file_path = read_ics_link()

    previous_event = None  # To keep track of the previously displayed event

    while True:
        print("Checking for next event")
        now = datetime.datetime.now().replace(tzinfo=None)
        
        # Check if it's the start of the hour
        perform_full_update = now.minute == 0
        
        next_event = get_next_event(file_path)

        if next_event:
            
            # Check if the event has changed, if so, do a full update
            if next_event != previous_event:
                perform_full_update = True
                previous_event = next_event

            display_next_event(epd, next_event, full_update=perform_full_update)

            # If the next event has started and we're less than 10 minutes into it, 
            # calculate sleep duration to be 10 minutes after the start of the event
            if next_event["start"] <= now <= (next_event["start"] + datetime.timedelta(minutes=10)):
                sleep_until = next_event["start"] + datetime.timedelta(minutes=10)
            else:  # Otherwise, just sleep until the start of the next event
                sleep_until = next_event["start"]
            
            sleep_duration = (sleep_until - now).total_seconds()
                       
        else:
            print("No upcoming events found. Checking again in 60 seconds.")
            sleep_duration = 60  # Sleep for 60 seconds before checking again

        # Sleep for the calculated duration (if positive) or for 60 seconds (if negative)
        sleep_duration = min(MAX_SLEEP_DURATION, max(sleep_duration, 60))
        print(f"Sleeping for {sleep_duration} seconds")
        time.sleep(sleep_duration)