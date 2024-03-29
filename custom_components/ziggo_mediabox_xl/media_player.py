"""
Support for interface with a Ziggo Mediabox XL.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.ziggo_mediabox_xl/
"""
import logging
import socket

import voluptuous as vol

from datetime import timedelta
from homeassistant.util import Throttle

from homeassistant.components.media_player import (
    MediaPlayerDevice, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PLAY,
    SUPPORT_PREVIOUS_TRACK, SUPPORT_SELECT_SOURCE, SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON)
from homeassistant.const import (
    CONF_HOST, CONF_NAME, STATE_OFF, STATE_PAUSED, STATE_PLAYING,
    STATE_IDLE, STATE_ON)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['ziggo-mediabox-xl==1.1.0']

_LOGGER = logging.getLogger(__name__)

DATA_KNOWN_DEVICES = 'ziggo_mediabox_xl_known_devices'

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

SUPPORT_ZIGGO = SUPPORT_TURN_ON | SUPPORT_TURN_OFF | \
    SUPPORT_NEXT_TRACK | SUPPORT_PAUSE | SUPPORT_PREVIOUS_TRACK | \
    SUPPORT_SELECT_SOURCE | SUPPORT_PLAY

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Ziggo Mediabox XL platform."""
    from ziggo_mediabox_xl import ZiggoMediaboxXL

    hass.data[DATA_KNOWN_DEVICES] = known_devices = set()

    # Is this a manual configuration?
    if config.get(CONF_HOST) is not None:
        host = config.get(CONF_HOST)
        name = config.get(CONF_NAME)
    elif discovery_info is not None:
        host = discovery_info.get('host')
        name = discovery_info.get('name')
    else:
        _LOGGER.error("Cannot determine device")
        return

    # Only add a device once, so discovered devices do not override manual
    # config.
    hosts = []
    ip_addr = socket.gethostbyname(host)
    if ip_addr not in known_devices:
        try:
            mediabox = ZiggoMediaboxXL(ip_addr)
            hosts.append(ZiggoMediaboxXLDevice(mediabox, host, name))
            known_devices.add(ip_addr)
        except socket.error as error:
            _LOGGER.error("Can't connect to %s: %s", host, error)
    else:
        _LOGGER.info("Ignoring duplicate Ziggo Mediabox XL %s", host)
    add_devices(hosts, True)


class ZiggoMediaboxXLDevice(MediaPlayerDevice):
    """Representation of a Ziggo Mediabox XL Device."""

    def __init__(self, mediabox, host, name):
        """Initialize the device."""
        # Generate a configuration for the Samsung library
        self._mediabox = mediabox
        self._host = host
        self._name = name
        self._state = None
        self._status = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Retrieve the state of the device."""
        try:
            if self._mediabox.test_connection() == True:
                self._state = STATE_IDLE
                self._status = 2
                
                if self._mediabox.turned_on() == True:
                    if self._state != STATE_PAUSED:
                        self._state = STATE_PLAYING
                    #self._state = STATE_PLAYING
                    #self._status = 1
                    
            else:
                self._state = STATE_OFF 
                self._status = 3                
        except socket.error:
            _LOGGER.error("Couldn't fetch state from %s", self._host)

    def send_keys(self, keys):
        """Send keys to the device and handle exceptions."""
        try:
            self._mediabox.send_keys(keys)
        except socket.error:
            _LOGGER.error("Couldn't send keys to %s", self._host)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def source_list(self):
        """List of available sources (channels)."""
        return [self._mediabox.channels()[c]
                for c in sorted(self._mediabox.channels().keys())]

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_ZIGGO
        
    @property
    def media_content_type(self):
        """Album name of current playing media, music track only."""
        if (self._status == 1) or (self._status == 2):
            return 'verbonden'
        else:
            return 'niet verbonden'

    def turn_on(self):
        """Turn the media player on."""
        if self._state is STATE_OFF or self._state is STATE_IDLE:
            self.send_keys(['POWER'])
            #self._state = STATE_ON

    def turn_off(self):
        """Turn off media player."""
        if self._state is not STATE_OFF:
            if self._state is STATE_IDLE:
                self.send_keys(['POWER'])
                #self._state = STATE_IDLE

    def media_play(self):
        """Send play command."""
        self.send_keys(['PLAY'])
        self._state = STATE_PLAYING

    def media_pause(self):
        """Send pause command."""
        self.send_keys(['PAUSE'])
        self._state = STATE_PAUSED

    def media_play_pause(self):
        """Simulate play pause media player."""
        self.send_keys(['PAUSE'])
        if self._state == STATE_PAUSED:
            self._state = STATE_PLAYING
        else:
            self._state = STATE_PAUSED

    def media_next_track(self):
        """Channel up."""
        self.send_keys(['CHAN_UP'])
        self._state = STATE_PLAYING

    def media_previous_track(self):
        """Channel down."""
        self.send_keys(['CHAN_DOWN'])
        self._state = STATE_PLAYING

    def select_source(self, source):
        """Select the channel."""
        if str(source).isdigit():
            digits = str(source)
        else:
            digits = next((
                key for key, value in self._mediabox.channels().items()
                if value == source), None)
        if digits is None:
            return

        self.send_keys(['NUM_{}'.format(digit)
                        for digit in str(digits)])
        self._state = STATE_PLAYING
