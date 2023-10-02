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
    for event in cal.walk("VEVENT"):
        print(event.get("summary"), event.get("dtstart").dt)
        break

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


def draw_event_details(draw, event):
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)

    # Prepare event details
    summary = f"Event: {event['summary']}"
    start_time = f"Start: {event['start'].strftime('%Y-%m-%d %H:%M')}"
    end_time = f"End: {event['end'].strftime('%Y-%m-%d %H:%M')}"
    location = f"Location: {event['location']}"

    # Draw event details on the image buffer
    draw.text((0, 0), summary, font=font, fill=0)
    draw.text((0, 20), start_time, font=font, fill=0)
    draw.text((0, 40), end_time, font=font, fill=0)
    draw.text((0, 60), location, font=font, fill=0)

FLIP_DISPLAY = False # Set this to True if you'd like to flip the display upside-down

def display_next_event(event):
    epd = epd2in13_V3.EPD()
    epd.init()

    # clear the screen
    epd.Clear(0xFF)

    # create the image buffer
    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    draw_event_details(draw, event)

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

if __name__ == "__main__":
    # !!!!! Be sure to open up ics_link_sample.txt and follow the instructions
    file_path = read_ics_link()

    while True:
        next_event = get_next_event(file_path)

        if next_event:
            display_next_event(next_event)

            # Calculate the time to sleep until 10 minutes after the start of the current event
            now = datetime.datetime.now().replace(tzinfo=None)
            sleep_until = next_event["start"] + datetime.timedelta(minutes=10)
            sleep_duration = (sleep_until - now).total_seconds()

            # Sleep for the calculated duration (if positive) or for 60 seconds (if negative)
            time.sleep(max(sleep_duration, 60))
        else:
            print("No upcoming events found.")
            time.sleep(60)  # Sleep for 60 seconds before checking again

