# calendardisplay
Displays your next meeting from an ICS file on a Waveshare epd2in13_V3 e-Ink display connected to a Raspberry Pi.
With minor modifications it could run on any waveshare e-Paper screen. Fork it! Fix it!

Follow these instructions to get your RPi configured first:
https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual

Too long, don't want to read?
Do this.

```sudo raspi-config```

Select Interfacing Options > SPI > Yes, enable SPI interface

```sudo reboot```

```
sudo apt-get update
sudo apt-get install python3-pip
sudo apt-get install python3-pil
sudo apt-get install python3-numpy
sudo pip3 install RPi.GPIO
sudo pip3 install spidev
```

Clone the Waveshare demo project which can build the waveshare_epd module

```git clone https://github.com/waveshare/e-Paper.git```

Install the waveshare_epd module and other dependencies

```python3 e-Paper/RaspberryPi_JetsonNano/python/setup.py install```

# Important Bits

1. Adding your personal calendar

    Be sure to open up ics_link_sample.txt and follow the instructions to rename it and add the link or path to your calendar.

2. But I don't use Microsoft 365!

    If you are using a local Exchange server (as opposed to a Cloud one), this other project may help you retrieve your ICS file directly from the Outlook desktop client.

    https://www.github.com/holotape/calendarexporter

3. It's Upside-Down!

    If the image is upside-down, look for this line in the display_next_event.py file

    ```python
    FLIP_DISPLAY = True # Set this to False if you'd like to flip the display rightside-up
    ```
    Set that to False to flip it around.
