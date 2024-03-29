import datetime
import time
import os
from icalendar import Calendar
import pytz
import requests

from waveshare_epd import epd2in13_V3
from PIL import Image, ImageDraw, ImageFont


def get_next_event(file_path_or_url):
    local_tz = pytz.timezone("America/Toronto")
    now = datetime.datetime.now(local_tz).replace(tzinfo=None)
    
    # Check if the input is a URL or a local file path
    if file_path_or_url.startswith("http://") or file_path_or_url.startswith("https://"):
        headers = {"Cache-Control": "no-cache"} # Don't cache the ICS file
        response = requests.get(file_path_or_url)
        response.raise_for_status()  # raise an exception if there was an error fetching the URL
        cal_content = response.content
    else:
        with open(file_path_or_url, "rb") as f:
            cal_content = f.read()

    cal = Calendar.from_ical(cal_content)

    next_event = None
    min_diff = float("inf")

    # for debugging purposes only
 #   for event in cal.walk("VEVENT"):
 #       print(event.get("summary"), event.get("dtstart").dt)
 #       break

    # logic
    next_event = None
    min_diff = float("inf")

    for event in cal.walk("VEVENT"):
        event_start_dt = event.get("dtstart").dt
        
        if isinstance(event_start_dt, datetime.datetime):
            event_start = event_start_dt.astimezone(local_tz).replace(tzinfo=None)
        else:  # it's a date, not a datetime
            event_start = event_start_dt
        
        if isinstance(event_start, datetime.datetime):  # handle both datetime and date types
            diff = (event_start - now).total_seconds()
        else:
            diff = float('inf')  # Treat all-day events like they're infinitely far in the future

        if 0 <= diff < min_diff:
            min_diff = diff
            next_event = {
                "summary": event.get("summary"),
                "start": event_start,
                "end": event.get("dtend").dt.replace(tzinfo=None),
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
    location = event['location'] or ''

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

MAX_SLEEP_DURATION = 600 # In seconds, 300 is 5 mins, 600 is 10, 900 is 15

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