import datetime
import time
import os
from icalendar import Calendar
import pytz

from waveshare_epd import epd2in13_V3
from PIL import Image, ImageDraw, ImageFont


def get_next_event(file_path):
    local_tz = pytz.timezone("America/Toronto")
    now = datetime.datetime.now(local_tz).replace(tzinfo=None)

    with open(file_path, "rb") as f:
        cal = Calendar.from_ical(f.read())

    next_event = None
    min_diff = float("inf")

    for event in cal.walk("VEVENT"):
        event_start = event.get("dtstart").dt.replace(tzinfo=None)
        diff = (event_start - now).total_seconds()

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
    # Set the font
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)

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


def display_next_event(event):
    epd = epd2in13_V3.EPD()
    epd.init()

    # Clear the screen
    epd.Clear(0xFF)

    # Create the image buffer
    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    # Draw event details
    draw_event_details(draw, event)

    # Display the image buffer
    epd.display(epd.getbuffer(image))

    # Put the display to sleep
    epd.sleep()


if __name__ == "__main__":
    # Make sure to replace this with the actual path to your .ics file
    file_path = "/home/pi/calendardisplay/calendar.ics"

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

